from pathlib import Path
from typing import List, Optional

# 定义识别模型的特征文件
TOKENIZER_PATTERNS = ["tokenizer*.json", "vocab.json", "merges.txt", "*.model", "special_tokens_map.json"]
IR_PATTERNS = ["*.xml", "openvino_model.xml"]

def _has_any(p: Path, globs: List[str], recursive: bool=False) -> bool:
    """检查目录下是否有符合 glob 模式的文件"""
    for g in globs:
        it = p.rglob(g) if recursive else p.glob(g)
        if any(it): return True
    return False

def _nearest_model_root(xml_dir: Path) -> Path:
    """
    向上查找包含 tokenizer 的根目录。
    有时候 xml 文件在子文件夹里（如 FP16/），但 tokenizer 在上层。
    """
    cur = xml_dir
    for _ in range(3): # 最多向上找3层
        if _has_any(cur, TOKENIZER_PATTERNS, recursive=False):
            return cur
        if cur.parent == cur: break
        cur = cur.parent
    return xml_dir

def scan_dirs(roots: List[Path], max_depth: int = 4):
    """
    扫描目录列表，返回所有有效的 OpenVINO 模型目录。
    """
    seen, found = set(), []
    
    def walk(root: Path, depth: int):
        if depth > max_depth or not root.exists(): return
        try:
            for d in root.iterdir():
                if not d.is_dir(): continue
                
                # 检查这里是否有 .xml 文件（IR模型）
                has_ir_here = _has_any(d, IR_PATTERNS, recursive=False)
                # 或者子目录里有 .xml
                has_ir_sub  = _has_any(d, IR_PATTERNS, recursive=True) if not has_ir_here else False
                
                if has_ir_here or has_ir_sub:
                    xml_dir = d
                    # 如果 xml 在子目录，找到具体那个子目录
                    if not has_ir_here:
                        for g in IR_PATTERNS:
                            hit = next(xml_dir.rglob(g), None)
                            if hit: 
                                xml_dir = hit.parent
                                break
                    
                    # 确定模型根目录 (包含 tokenizer 的那一层)
                    model_root = _nearest_model_root(xml_dir)
                    key = str(model_root.resolve())
                    
                    # 避免重复添加，并确保该目录也是有效的（有 tokenizer）
                    if key not in seen and _has_any(model_root, TOKENIZER_PATTERNS, recursive=False):
                        seen.add(key)
                        found.append({"name": model_root.name, "path": key})
                
                # 继续深搜
                walk(d, depth + 1)
        except PermissionError:
            pass
            
    for r in roots: 
        try: walk(r, 0)
        except Exception: pass
        
    # 按名称排序
    found.sort(key=lambda x: x["name"].lower())
    return found