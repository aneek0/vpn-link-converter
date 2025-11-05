"""CLI утилита для конвертации VPN ссылок"""
import sys
import json
from src.converter.singbox import convert_to_singbox, format_json, create_full_config
from src.converter.clash import convert_to_clash, convert_multiple_to_clash, format_yaml
from src.converter.xray import convert_multiple_to_xray, format_json as format_xray_json
from src.converter.parser import VPNLinkParser
from src.converter.subscription_sync import parse_subscription_sync, is_subscription_url


def main():
    """Главная функция CLI"""
    print("=" * 60)
    print("🔐 VPN Link Converter - Конвертер в sing-box")
    print("=" * 60)
    print()
    
    # Запрашиваем ссылку
    print("Вставьте VPN ссылку или подписку:")
    print("(Поддерживаются: hy2://, vless://, vmess://, trojan://, ss:// и др.)")
    print("(Также поддерживаются подписки: http/https ссылки, base64, текст с несколькими ссылками)")
    print()
    
    vpn_link = input("> ").strip()
    
    if not vpn_link:
        print("❌ Ошибка: ссылка не может быть пустой")
        sys.exit(1)
    
    # Переменная для хранения множественных ссылок из подписки
    subscription_links = None
    
    # Проверяем, является ли это подпиской
    try:
        if is_subscription_url(vpn_link):
            print("🔄 Обнаружена подписка, извлекаю VPN ссылки...")
            vpn_links = parse_subscription_sync(vpn_link)
            
            if not vpn_links:
                print("❌ Ошибка: не удалось извлечь VPN ссылки из подписки")
                sys.exit(1)
            
            if len(vpn_links) > 1:
                print(f"\n✅ Извлечено {len(vpn_links)} VPN ссылок из подписки\n")
                
                print("Выберите действие:")
                print("1. Экспортировать все ссылки в выбранном формате")
                print("2. Выбрать одну ссылку для конвертации")
                print("3. Выход")
                print()
                
                action = input("Выбор (1, 2 или 3, по умолчанию 1): ").strip()
                
                if action == "1" or not action:
                    # Сохраняем все ссылки для последующей конвертации
                    subscription_links = vpn_links
                    vpn_link = None  # Помечаем что это подписка
                elif action == "3":
                    print("Выход...")
                    sys.exit(0)
                else:
                    print("\nСписок ссылок:")
                    for i, link in enumerate(vpn_links, 1):
                        print(f"{i}. {link[:80]}...")
                    print()
                    choice = input("Выберите номер ссылки для конвертации: ").strip()
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(vpn_links):
                            vpn_link = vpn_links[idx]
                            subscription_links = None
                        else:
                            print("❌ Ошибка: неверный номер ссылки")
                            sys.exit(1)
                    except ValueError:
                        print("❌ Ошибка: введите число")
                        sys.exit(1)
            else:
                vpn_link = vpn_links[0]
                subscription_links = None
    except Exception as e:
        print(f"⚠️  Ошибка при парсинге подписки: {e}")
        print("Продолжаю обработку как обычной ссылки...\n")
        subscription_links = None
    
    # Проверяем протокол только если есть одна ссылка (не подписка)
    has_subscription = 'subscription_links' in locals() and subscription_links is not None
    if vpn_link and not has_subscription:
        try:
            protocol = VPNLinkParser.detect_protocol(vpn_link)
            if not protocol:
                print(f"❌ Ошибка: неподдерживаемый протокол")
                sys.exit(1)
            print(f"✅ Распознан протокол: {protocol.upper()}")
        except Exception as e:
            print(f"❌ Ошибка при определении протокола: {e}")
            sys.exit(1)
    
    print()
    if has_subscription:
        # Форматы для подписок
        print("Выберите формат экспорта подписки:")
        print("1. Текстовый файл (список ссылок)")
        print("2. Clash YAML")
        print("3. sing-box JSON (полная конфигурация)")
        print("4. Xray Core JSON")
        print()
        
        choice = input("Выбор (1, 2, 3 или 4, по умолчанию 2): ").strip()
        
        if choice == "1":
            format_type = "text"
            format_name = "Текстовый файл"
        elif choice == "2" or not choice:
            format_type = "clash"
            format_name = "Clash YAML"
        elif choice == "3":
            format_type = "singbox"
            format_name = "sing-box JSON (полная конфигурация)"
        elif choice == "4":
            format_type = "xray"
            format_name = "Xray Core JSON"
        else:
            format_type = "clash"
            format_name = "Clash YAML"
    else:
        # Форматы для одиночных ссылок
        print("Выберите формат конфигурации:")
        print("1. Полная конфигурация sing-box (log, dns, inbounds, outbounds, route)")
        print("2. Только outbound sing-box")
        print("3. Clash YAML")
        print()
        
        choice = input("Выбор (1, 2 или 3, по умолчанию 2): ").strip()
        
        if choice == "3":
            format_type = "clash"
            format_name = "Clash YAML"
        else:
            format_type = "singbox"
            full_config = choice == "1"
            format_name = "полная конфигурация sing-box" if full_config else "только outbound sing-box"
    
    print()
    print(f"🔄 Конвертация в формат: {format_name}...")
    print()
    
    try:
        # Проверяем, есть ли множественные ссылки из подписки
        if has_subscription:
            # Конвертируем все ссылки из подписки
            if format_type == "text":
                # Текстовый файл
                file_content = "\n".join(subscription_links)
                
                print("=" * 60)
                print("✅ Результат экспорта:")
                print("=" * 60)
                print()
                print(file_content)
                print()
                print("=" * 60)
                
                save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
                if save == 'y':
                    filename = input("Имя файла (по умолчанию: subscription.txt): ").strip()
                    if not filename:
                        filename = "subscription.txt"
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(file_content)
                        print(f"✅ Файл сохранен: {filename}")
                    except Exception as e:
                        print(f"❌ Ошибка при сохранении файла: {e}")
                        sys.exit(1)
            elif format_type == "clash":
                config = convert_multiple_to_clash(subscription_links)
                yaml_config = format_yaml(config)
                
                print("=" * 60)
                print("✅ Результат конвертации:")
                print("=" * 60)
                print()
                print(yaml_config)
                print()
                print("=" * 60)
                
                save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
                if save == 'y':
                    filename = input("Имя файла (по умолчанию: clash-config.yaml): ").strip()
                    if not filename:
                        filename = "clash-config.yaml"
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(yaml_config)
                        print(f"✅ Конфигурация сохранена в файл: {filename}")
                    except Exception as e:
                        print(f"❌ Ошибка при сохранении файла: {e}")
                        sys.exit(1)
            elif format_type == "singbox":
                # sing-box JSON (полная конфигурация)
                outbounds = []
                for link in subscription_links:
                    try:
                        outbound = VPNLinkParser.to_singbox_outbound(link)
                        outbounds.append(outbound)
                    except Exception:
                        continue
                
                if not outbounds:
                    print("❌ Ошибка: не удалось конвертировать ни одну ссылку")
                    sys.exit(1)
                
                config = create_full_config(outbounds)
                json_config = format_json(config)
                
                print("=" * 60)
                print("✅ Результат конвертации:")
                print("=" * 60)
                print()
                print(json_config)
                print()
                print("=" * 60)
                
                save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
                if save == 'y':
                    filename = input("Имя файла (по умолчанию: sing-box-config.json): ").strip()
                    if not filename:
                        filename = "sing-box-config.json"
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(json_config)
                        print(f"✅ Конфигурация сохранена в файл: {filename}")
                    except Exception as e:
                        print(f"❌ Ошибка при сохранении файла: {e}")
                        sys.exit(1)
            elif format_type == "xray":
                # Xray Core JSON
                config = convert_multiple_to_xray(subscription_links)
                json_config = format_xray_json(config)
                
                print("=" * 60)
                print("✅ Результат конвертации:")
                print("=" * 60)
                print()
                print(json_config)
                print()
                print("=" * 60)
                
                save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
                if save == 'y':
                    filename = input("Имя файла (по умолчанию: xray-config.json): ").strip()
                    if not filename:
                        filename = "xray-config.json"
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(json_config)
                        print(f"✅ Конфигурация сохранена в файл: {filename}")
                    except Exception as e:
                        print(f"❌ Ошибка при сохранении файла: {e}")
                        sys.exit(1)
        elif format_type == "clash":
            config = convert_to_clash(vpn_link)
            yaml_config = format_yaml(config)
            
            # Выводим результат
            print("=" * 60)
            print("✅ Результат конвертации:")
            print("=" * 60)
            print()
            print(yaml_config)
            print()
            print("=" * 60)
            
            # Предлагаем сохранить в файл
            save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
            
            if save == 'y':
                filename = input("Имя файла (по умолчанию: clash-config.yaml): ").strip()
                if not filename:
                    filename = "clash-config.yaml"
                
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(yaml_config)
                    print(f"✅ Конфигурация сохранена в файл: {filename}")
                except Exception as e:
                    print(f"❌ Ошибка при сохранении файла: {e}")
                    sys.exit(1)
        else:
            config = convert_to_singbox(vpn_link, full_config=full_config)
            json_config = format_json(config)
            
            # Выводим результат
            print("=" * 60)
            print("✅ Результат конвертации:")
            print("=" * 60)
            print()
            print(json_config)
            print()
            print("=" * 60)
            
            # Предлагаем сохранить в файл
            save = input("Сохранить в файл? (y/n, по умолчанию n): ").strip().lower()
            
            if save == 'y':
                filename = input("Имя файла (по умолчанию: sing-box-config.json): ").strip()
                if not filename:
                    filename = "sing-box-config.json"
                
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(json_config)
                    print(f"✅ Конфигурация сохранена в файл: {filename}")
                except Exception as e:
                    print(f"❌ Ошибка при сохранении файла: {e}")
                    sys.exit(1)
        
        print()
        print("✨ Готово!")
        
    except Exception as e:
        print(f"❌ Ошибка при конвертации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем")
        sys.exit(0)

