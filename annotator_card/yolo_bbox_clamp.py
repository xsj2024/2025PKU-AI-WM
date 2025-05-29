import os

def clamp(value, min_val=0.0, max_val=1.0):
    """确保值在 [min_val, max_val] 范围内"""
    return max(min_val, min(value, max_val))

def process_file(file_path):
    """处理单个YOLO格式文件"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:  # 确保是有效的YOLO格式行
            new_lines.append(line)
            continue
            
        # 解析YOLO格式数据
        class_id = parts[0]
        x_center = float(parts[1])
        y_center = float(parts[2])
        width = float(parts[3])
        height = float(parts[4])
        
        # 检查并修正边界框
        new_x = clamp(x_center)
        new_y = clamp(y_center)
        
        # 确保宽度和高度不超过边界
        new_width = clamp(width, 0.0, 2 * min(new_x, 1 - new_x))
        new_height = clamp(height, 0.0, 2 * min(new_y, 1 - new_y))
        
        # 检查是否有任何修改
        if (x_center != new_x or y_center != new_y or 
            width != new_width or height != new_height):
            modified = True
        
        # 构建修正后的行
        new_line = f"{class_id} {new_x:.6f} {new_y:.6f} {new_width:.6f} {new_height:.6f}\n"
        new_lines.append(new_line)
    
    # 如果有修改，则保存文件
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print(f"已修正: {file_path}")
    else:
        print(f"无需修正: {file_path}")

def process_folder(folder_path):
    """处理文件夹下所有YOLO格式文件"""
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            process_file(file_path)

if __name__ == "__main__":
    import sys
    from .config import Config
    folder_path = os.path.join(Config.YOLO_DATA_DIR_REAL,"labels")
    if not os.path.isdir(folder_path):
        print(f"错误: {folder_path} 不是一个有效的文件夹")
        sys.exit(1)
        
    print(f"开始处理文件夹: {folder_path}")
    process_folder(folder_path)
    print("处理完成!")
