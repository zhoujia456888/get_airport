import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

# 设置请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

# 目标URL
url = 'https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9B%BD%E6%9C%BA%E5%9C%BA%E8%BF%90%E8%90%A5%E7%BB%9F%E8%AE%A1%E5%88%97%E8%A1%A8'

def get_airport_coordinates(airport_url):
    """获取机场详情页面中的地理位置坐标"""
    try:
        # 请求机场详情页面
        response = requests.get(airport_url, headers=headers)
        if response.status_code != 200:
            print(f"无法访问机场详情页面: {airport_url}")
            return None, None

        # 解析页面内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找经纬度信息
        # 方法1: 尝试查找geo-multi-punctuation类元素
        geo_element = soup.find('span', class_='geo-multi-punctuation')
        if geo_element:
            coordinates = geo_element.parent.get_text(strip=True)
            lat, lon = coordinates.split(';')
            return lat.strip(), lon.strip()

        # 方法2: 尝试查找合并显示的经纬度（如"坐标：25°04′48″N 102°42′30″E"）
        coordinate_text = None

        # 查找包含"坐标"文本的th或td标签
        coord_header = soup.find(lambda tag: tag.name in ['th', 'td'] and '坐标' in tag.get_text(strip=True))
        if coord_header:
            # 坐标值通常在相邻的td标签中
            parent_row = coord_header.parent
            if parent_row:
                sibling_cells = parent_row.find_all('td')
                for i, cell in enumerate(sibling_cells):
                    if cell == coord_header and i+1 < len(sibling_cells):
                        coordinate_text = sibling_cells[i+1].get_text(strip=True)
                        break

        # 如果没找到，尝试更宽泛的搜索
        if not coordinate_text:
            coord_element = soup.find(lambda tag: tag.name in ['p', 'div'] and '坐标' in tag.get_text(strip=True))
            if coord_element:
                coordinate_text = coord_element.get_text(strip=True)

        # 处理找到的坐标文本
        if coordinate_text:
           # print(f"找到坐标文本: {coordinate_text}")

            # 尝试提取十进制格式
            decimal_match = re.search(r'(\d+\.\d+);\s*(\d+\.\d+)', coordinate_text)
            if decimal_match:
                return decimal_match.group(1), decimal_match.group(2)

            # 尝试提取度分秒格式
            dms_match = re.search(r'(\d+)[°度]\s*(\d+)[′分]\s*(\d+)[″秒]\s*([NS])\s*(\d+)[°度]\s*(\d+)[′分]\s*(\d+)[″秒]\s*([EW])', coordinate_text)
            if dms_match:
                # 解析度分秒格式
                lat_deg, lat_min, lat_sec, lat_dir = dms_match.group(1, 2, 3, 4)
                lon_deg, lon_min, lon_sec, lon_dir = dms_match.group(5, 6, 7, 8)

                # 转换为十进制
                lat = float(lat_deg) + float(lat_min)/60 + float(lat_sec)/3600
                lon = float(lon_deg) + float(lon_min)/60 + float(lon_sec)/3600

                # 调整南北纬和东西经
                if lat_dir == 'S':
                    lat = -lat
                if lon_dir == 'W':
                    lon = -lon

                return str(lat), str(lon)

            print("无法解析坐标格式")

        # 方法3: 尝试查找data-lat和data-lon属性
        lat_element = soup.find(attrs={'data-lat': True})
        lon_element = soup.find(attrs={'data-lon': True})
        if lat_element and lon_element:
            return lat_element['data-lat'], lon_element['data-lon']

        print(f"未在页面 {airport_url} 上找到经纬度信息")
        return None, None

    except Exception as e:
        print(f"获取经纬度时出错: {e}")
        return None, None

try:
    # 发送请求
    response = requests.get(url, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找所有表格
        tables = soup.find_all('table', class_='wikitable')

        # 用于存储机场数据的列表
        airports = []

        # 打印调试信息
        print(f"找到 {len(tables)} 个表格")

        # 处理每个表格
        for table_idx, table in enumerate(tables):
            print(f"\n处理表格 {table_idx + 1}/{len(tables)}")

            # 查找表格中的所有行
            rows = table.find_all('tr')

            # 尝试多种标题行识别方式
            title_row = None
            for i, row in enumerate(rows):
                row_text = ' '.join(cell.get_text(strip=True) for cell in row.find_all(['th', 'td']))
                # 检查是否包含关键列名组合
                if ('机场名称' in row_text) and ('IATA' in row_text) and ('ICAO' in row_text):
                    title_row = i
                    print(f"找到标题行在位置 {title_row}")
                    break

            # 如果未找到标准标题行，尝试宽松匹配
            if title_row is None:
                for i, row in enumerate(rows):
                    row_text = ' '.join(cell.get_text(strip=True) for cell in row.find_all(['th', 'td']))
                    if ('机场' in row_text) and ('IATA' in row_text):
                        title_row = i
                        print(f"找到宽松匹配的标题行在位置 {title_row}")
                        break

            # 如果找到标题行，则从下一行开始处理数据
            if title_row is not None:
                # 获取列索引
                header_cells = rows[title_row].find_all(['th', 'td'])
                headers_text = [cell.get_text(strip=True) for cell in header_cells]

                # 查找"机场名称"、"IATA"、"ICAO"和"省份"的列索引
                name_index = next((i for i, h in enumerate(headers_text) if '机场名称' in h), -1)
                iata_index = next((i for i, h in enumerate(headers_text) if 'IATA' in h), -1)
                icao_index = next((i for i, h in enumerate(headers_text) if 'ICAO' in h), -1)
                province_index = next((i for i, h in enumerate(headers_text) if '省份' in h), -1)

                # 打印调试信息
                print(f"列索引: 名称={name_index}, IATA={iata_index}, ICAO={icao_index}, 省份={province_index}")

                # 如果缺少必要的列，则跳过此表格
                if name_index == -1 or iata_index == -1 or icao_index == -1:
                    print("缺少必要的列，跳过此表格")
                    continue

                # 处理数据行
                table_airports = 0
                for row_idx, row in enumerate(rows[title_row + 1:]):
                    cells = row.find_all(['th', 'td'])

                    # 确保有足够的单元格
                    if len(cells) <= max(name_index, iata_index, icao_index):
                        print(f"行 {row_idx + 1}: 单元格数量不足，跳过")
                        continue

                    # 获取原始单元格文本
                    name_text = cells[name_index].get_text(strip=True)
                    iata_text = cells[iata_index].get_text(strip=True)
                    icao_text = cells[icao_index].get_text(strip=True)
                    province_text = cells[province_index].get_text(strip=True) if province_index != -1 else ""

                    # 提取IATA和ICAO代码（处理可能的格式问题）
                    iata_match = re.search(r'([A-Z]{3})', iata_text)
                    icao_match = re.search(r'(ZB|ZJ|ZS|ZU|ZW|ZY[A-Z]{2})', icao_text)

                    iata_code = iata_match.group(1) if iata_match else iata_text
                    icao_code = icao_match.group(1) if icao_match else icao_text

                    # 获取机场名称和链接
                    name_cell = cells[name_index]
                    name_link = name_cell.find('a')
                    airport_name = name_link.get_text(strip=True) if name_link else name_text

                    # 构建机场详情页面URL
                    airport_url = None
                    if name_link and name_link.get('href'):
                        airport_url = urljoin(url, name_link.get('href'))

                    # 过滤掉非机场数据（放宽条件）
                    valid_iata = re.match(r'^[A-Z]{3}$', iata_code)
                    valid_icao = re.match(r'^ZB|ZJ|ZS|ZU|ZW|ZY[A-Z]{2}$', icao_code)

                    # 打印详细的行处理信息
                    print(f"行 {row_idx + 1}: 名称='{airport_name}', IATA='{iata_code}', ICAO='{icao_code}', 省份='{province_text}'")
                    print(f"        验证结果: IATA={valid_iata}, ICAO={valid_icao}")

                    # 放宽筛选条件，只要IATA或ICAO有效就保留
                    if valid_iata or valid_icao:
                        # 初始化坐标
                        latitude = None
                        longitude = None

                        # 如果有机场链接，则获取坐标
                        if airport_url:
                            print(f"    获取机场坐标: {airport_url}")
                            latitude, longitude = get_airport_coordinates(airport_url)
                            print(f"    坐标: 纬度={latitude}, 经度={longitude}")

                        # 添加机场数据到列表
                        airports.append({
                            'name': airport_name,
                            'iata': iata_code,
                            'icao': icao_code,
                            'province': province_text,
                            'latitude': latitude,
                            'longitude': longitude,
                            'url': airport_url
                        })
                        table_airports += 1
                        print(f"        ✅ 已添加")

                print(f"从表格 {table_idx + 1} 中提取了 {table_airports} 个机场数据")
            else:
                print(f"未找到此表格的标题行，跳过")

        # 导出为JSON文件
        with open('chinese_airports.json', 'w', encoding='utf-8') as f:
            json.dump(airports, f, ensure_ascii=False, indent=4)

        print(f"\n成功爬取并导出 {len(airports)} 个机场数据到 chinese_airports.json")

    else:
        print(f"请求失败，状态码: {response.status_code}")

except Exception as e:
    print(f"发生错误: {e}")