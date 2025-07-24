import requests
from bs4 import BeautifulSoup
import json
import re

def get_airport_data():
    url = "https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9B%BD%E6%9C%BA%E5%9C%BA%E5%88%97%E8%A1%A8"

    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    try:
        # 发送HTTP请求
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查请求是否成功

        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找所有表格
        tables = soup.find_all('table', class_='wikitable')

        # 存储机场信息的列表
        airports = []

        # 遍历每个表格
        for table in tables:
            # 获取表头
            headers = []
            for th in table.find('tr').find_all(['th', 'td']):
                header_text = th.get_text(strip=True)
                headers.append(header_text)

            # 查找机场名称、ICAO、IATA等列的索引
            name_index = -1
            icao_index = -1
            iata_index = -1
            type_index = -1
            city_index = -1

            for i, header in enumerate(headers):
                if '机场名称' in header or '名称' in header:
                    name_index = i
                elif 'ICAO' in header:
                    icao_index = i
                elif 'IATA' in header:
                    iata_index = i
                elif '性质' in header:
                    type_index = i
                elif '服务城市' in header or '所在城市' in header:
                    city_index = i

            # 提取表格中的数据行
            rows = table.find_all('tr')[1:]  # 跳过表头行

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < max(name_index, icao_index, iata_index, type_index, city_index) + 1:
                    continue  # 跳过不完整的行

                # 提取ICAO、IATA、性质和城市信息
                icao = cells[icao_index].get_text(strip=True) if icao_index >= 0 else ""
                iata = cells[iata_index].get_text(strip=True) if iata_index >= 0 else ""

                # 跳过IATA为空或为'-'的数据
                if not iata or iata == '-':
                    continue

                # 提取机场名称并分割中英文
                name_cell = cells[name_index]
                name_text = name_cell.get_text(strip=True)

                # 尝试分割中英文名称
                chinese_name = ''
                english_name = ''

                # 处理常见的中英文分隔模式
                if '(' in name_text and ')' in name_text:
                    # 模式：中文(英文)
                    parts = re.split(r'[()]', name_text)
                    chinese_name = parts[0].strip()
                    english_name = parts[1].strip() if len(parts) > 1 else ''
                elif '（' in name_text and '）' in name_text:
                    # 模式：中文（英文）
                    parts = re.split(r'[（）]', name_text)
                    chinese_name = parts[0].strip()
                    english_name = parts[1].strip() if len(parts) > 1 else ''
                else:
                    # 使用正则表达式提取中文和英文
                    chinese_match = re.search(r'[\u4e00-\u9fff]+', name_text)
                    english_match = re.search(r'[a-zA-Z\s]+', name_text)

                    chinese_name = chinese_match.group(0).strip() if chinese_match else ''
                    english_name = english_match.group(0).strip() if english_match else ''

                # 如果中文名称提取失败，使用整个名称文本
                if not chinese_name:
                    chinese_name = name_text

                airport_type = cells[type_index].get_text(strip=True) if type_index >= 0 else ""
                city = cells[city_index].get_text(strip=True) if city_index >= 0 else ""

                # 添加到机场列表，使用英文字段名
                airports.append({
                    "nameChinese": chinese_name,
                    "nameEnglish": english_name,
                    "icaoCode": icao,
                    "iataCode": iata,
                    "airportType": airport_type,
                    "serviceCity": city
                })

        return airports

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return []
    except Exception as e:
        print(f"发生错误: {e}")
        return []

def save_to_json(data, filename='chinese_airports.json'):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"数据已成功保存到 {filename}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    # 获取机场数据
    airport_data = get_airport_data()

    # 保存为JSON文件
    if airport_data:
        save_to_json(airport_data)
        print(f"共获取到 {len(airport_data)} 个机场数据")
    else:
        print("未能获取到机场数据")