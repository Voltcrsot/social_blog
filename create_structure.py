import os
import sys

# Директории, которые нужно полностью исключить из вывода
EXCLUDE_DIRS = {'venv', '__pycache__', 'node_modules', '.git', '.idea', '.vscode'}
# Файлы, которые нужно игнорировать в листинге (по желанию)
EXCLUDE_FILES = {'.DS_Store', '.env'} # .env можно добавить, если не хотите его показывать

def list_project_structure(start_path, indent=''):
    """
    Рекурсивно обходит директории и печатает структуру.
    """
    # Исключаем саму папку, если она в списке исключений
    if os.path.basename(start_path) in EXCLUDE_DIRS:
        return

    try:
        # Получаем список файлов и папок, сортируем для порядка
        items = sorted(os.listdir(start_path))
    except OSError as e:
        print(f"{indent}└── [Не удалось прочитать папку: {e}]")
        return

    files = [item for item in items if os.path.isfile(os.path.join(start_path, item)) and item not in EXCLUDE_FILES and not item.startswith('.')]
    dirs = [item for item in items if os.path.isdir(os.path.join(start_path, item)) and item not in EXCLUDE_DIRS and not item.startswith('.')]

    # Печатаем директории сначала
    for i, name in enumerate(dirs):
        is_last = (i == len(dirs) - 1) and (len(files) == 0) # Последний элемент *всего* списка?
        connector = '└── ' if is_last else '├── '
        print(f"{indent}{connector}{name}/")
        new_indent = indent + ('    ' if is_last else '│   ')
        list_project_structure(os.path.join(start_path, name), new_indent)

    # Печатаем файлы
    for i, name in enumerate(files):
        is_last = (i == len(files) - 1) # Последний файл?
        connector = '└── ' if is_last else '├── '
        print(f"{indent}{connector}{name}")


if __name__ == "__main__":
    # Получаем путь к директории, ИЗ КОТОРОЙ запущен скрипт
    current_working_directory = os.getcwd()
    project_name = os.path.basename(current_working_directory)

    print(f"{project_name}/") # Печатаем корневую папку
    list_project_structure(current_working_directory)
    print("-" * 40)
    print("Примечание: Папки {}, а также файлы {} и скрытые файлы/папки (начинающиеся с '.') были пропущены.".format(
        ", ".join(sorted(EXCLUDE_DIRS)),
        ", ".join(sorted(EXCLUDE_FILES))
    ))
    print("Структура показана для директории:", current_working_directory)