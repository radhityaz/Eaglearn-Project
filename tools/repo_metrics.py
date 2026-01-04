import os
import json
from collections import defaultdict

# Direktori yang akan dihitung
DIRECTORIES = [
    'backend',
    'frontend',
    'prototypes',
    'eaglearn-clone',
    'copy/focus-coach',
    'spec',
    'docs',
    'tests',
    'benchmarks',
    'models',
    'proto'
]

# Ekstensi yang dianggap sebagai kode
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.css', '.html', '.md', '.json'}

# File yang akan dikecualikan
EXCLUDED_FILES = {
    # PDF files
    'science-source/*.pdf',
    # SVG files
    'eaglearn-clone/assets/icons/*.svg',
    'prototypes/figma-export/icons/*.svg',
    # Image files
    'prototypes/figma-export/screenshots/*.*',
    # Biner lainnya
    '*.zip', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.mp4', '*.mov', '*.webm', '*.wav'
}

def is_excluded_file(filepath):
    """Periksa apakah file termasuk dalam pengecualian"""
    # Untuk keperluan sederhana, kita gunakan ekstensi saja
    _, ext = os.path.splitext(filepath)
    
    # Kecualikan file biner
    binary_ext = {'.pdf', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.mp4', '.mov', '.webm', '.wav'}
    if ext.lower() in binary_ext:
        return True
    
    # Kecualikan file SVG di direktori tertentu
    if 'eaglearn-clone/assets/icons/' in filepath or 'prototypes/figma-export/icons/' in filepath:
        if ext.lower() == '.svg':
            return True
            
    # Kecualikan gambar di screenshots
    if 'prototypes/figma-export/screenshots/' in filepath:
        if ext.lower() in {'.png', '.jpg', '.jpeg', '.gif'}:
            return True
    
    return False

def estimate_loc(filepath):
    """Estimasi baris kode dari file teks"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0

def get_directory_metrics():
    """Hitung metrik untuk setiap direktori"""
    metrics = {
        'summary': {
            'total_files': 0,
            'total_code_files': 0,
            'total_size_bytes': 0,
            'approx_total_loc': 0
        },
        'per_directory': {},
        'extension_histogram': {}
    }
    
    # Inisialisasi histogram ekstensi
    for ext in CODE_EXTENSIONS:
        metrics['extension_histogram'][ext] = {'file_count': 0, 'approx_loc': 0}
    
    for dir_path in DIRECTORIES:
        if not os.path.exists(dir_path):
            continue
            
        dir_metrics = {
            'files': 0,
            'code_files': 0,
            'size_bytes': 0,
            'approx_loc': 0
        }
        
        # Iterasi melalui semua file dalam direktori
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Periksa apakah file dikecualikan
                if is_excluded_file(filepath):
                    continue
                    
                # Hitung statistik file
                dir_metrics['files'] += 1
                metrics['summary']['total_files'] += 1
                
                # Hitung ukuran file
                try:
                    file_size = os.path.getsize(filepath)
                    dir_metrics['size_bytes'] += file_size
                    metrics['summary']['total_size_bytes'] += file_size
                except OSError:
                    pass
                
                # Hitung baris kode
                _, ext = os.path.splitext(file)
                loc = estimate_loc(filepath)
                dir_metrics['approx_loc'] += loc
                metrics['summary']['approx_total_loc'] += loc
                
                # Perbarui histogram ekstensi
                if ext.lower() in CODE_EXTENSIONS:
                    dir_metrics['code_files'] += 1
                    metrics['summary']['total_code_files'] += 1
                    metrics['extension_histogram'][ext.lower()]['file_count'] += 1
                    metrics['extension_histogram'][ext.lower()]['approx_loc'] += loc
        
        metrics['per_directory'][dir_path] = dir_metrics
    
    return metrics

if __name__ == "__main__":
    result = get_directory_metrics()
    
    # Simpan ke file METRICS.json
    os.makedirs('metrics', exist_ok=True)
    with open('metrics/METRICS.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("Metrik telah disimpan ke metrics/METRICS.json")