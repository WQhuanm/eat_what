"""
提取指定目录下所有 JSON 文件中的商家名称并保存到 txt
"""
import json
from pathlib import Path


def extract_shop_names(directory: str, output_file: str = None) -> list:
    """
    从目录下的所有 JSON 文件中提取 shop_name
    
    Args:
        directory: JSON 文件所在目录
        output_file: 输出 txt 文件路径，默认在同一目录生成 shop_names.txt
    
    Returns:
        list: 所有提取到的商家名称列表
    """
    target_dir = Path(directory)
    if not target_dir.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    if output_file is None:
        output_file = target_dir / "shop_names.txt"
    else:
        output_file = Path(output_file)
    
    shop_names = []
    json_files = list(target_dir.glob("*.json"))
    
    print(f"发现 {len(json_files)} 个 JSON 文件")
    
    for json_file in sorted(json_files):
        print(f"\n正在解析: {json_file.name}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 支持两种格式：
            # 1. 直接是数组 [{"shop_name": "xxx", ...}, ...]
            # 2. 单个对象 {"shop_name": "xxx", ...}
            if isinstance(data, list):
                shops = data
            else:
                shops = [data]
            
            file_shops = []
            for shop in shops:
                if isinstance(shop, dict) and shop.get("shop_name"):
                    name = shop["shop_name"].strip()
                    if name and name not in shop_names:
                        shop_names.append(name)
                        file_shops.append(name)
            
            print(f"  提取到 {len(file_shops)} 个商家")
            for name in file_shops:
                print(f"    - {name}")
                
        except json.JSONDecodeError as e:
            print(f"  错误: JSON 解析失败 - {e}")
        except Exception as e:
            print(f"  错误: {e}")
    
    # 写入 txt 文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 商家名称列表\n")
        f.write(f"# 提取目录: {directory}\n")
        f.write(f"# 总计: {len(shop_names)} 个商家\n")
        f.write(f"# {'='*50}\n\n")
        
        for i, name in enumerate(shop_names, 1):
            f.write(f"{i}. {name}\n")
    
    print(f"\n{'='*50}")
    print(f"提取完成！总计 {len(shop_names)} 个唯一商家")
    print(f"结果已保存至: {output_file}")
    
    return shop_names


if __name__ == "__main__":
    import sys
    
    # 默认目录
    default_dir = r"D:\_Project_File\eat_what\get_data\.generated"
    
    # 支持命令行参数传入目录
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    
    extract_shop_names(target_dir)
