"""Роуты для веб-сайта"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path

from ..converter.singbox import convert_to_singbox, format_json, create_full_config
from ..converter.clash import convert_to_clash, convert_multiple_to_clash, format_yaml
from ..converter.xray import convert_multiple_to_xray, format_json as format_xray_json
from ..converter.parser import VPNLinkParser
from ..converter.subscription_sync import parse_subscription_sync
from ..converter.subscription import is_subscription_url
from urllib.parse import urlparse
import re

router = APIRouter()

# Инициализация шаблонов
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


class ConvertRequest(BaseModel):
    """Модель запроса на конвертацию"""
    url: str
    full_config: bool = False


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/api/convert")
async def convert_api(request: ConvertRequest):
    """API endpoint для конвертации"""
    try:
        config = convert_to_singbox(request.url, full_config=request.full_config)
        json_config = format_json(config)
        
        return JSONResponse({
            "success": True,
            "config": config,
            "json": json_config,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/detect-type")
async def detect_type(url: str = Form(...)):
    """API endpoint для определения типа ссылки"""
    try:
        is_subscription = is_subscription_url(url)
        
        # Проверяем, является ли это VPN протоколом
        vpn_protocols = [
            'hy2://', 'hysteria2://', 'vless://', 'vmess://', 'trojan://',
            'ss://', 'shadowsocks://', 'socks5://', 'socks://',
            'wg://', 'wireguard://', 'tuic://', 'hysteria://'
        ]
        is_vpn_link = any(url.strip().startswith(proto) for proto in vpn_protocols)
        
        return JSONResponse({
            "is_subscription": is_subscription,
            "is_vpn_link": is_vpn_link,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def generate_filename_from_url(url: str, extension: str, format_type: str = None) -> str:
    """Генерирует имя файла из URL"""
    if not url:
        if format_type == "clash":
            return "clash-config.yaml"
        elif format_type == "xray":
            return "xray-config.json"
        elif format_type == "full":
            return "sing-box-config.json"
        elif format_type == "outbound":
            return "sing-box-outbound.json"
        return f"config.{extension}"
    
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or parsed.netloc
        if hostname:
            if ':' in hostname:
                hostname = hostname.split(':')[0]
            hostname = re.sub(r'[<>:"/\\|?*]', '-', hostname)
            if len(hostname) > 50:
                hostname = hostname[:50]
            return f"{hostname}.{extension}"
    except Exception:
        pass
    
    if format_type == "clash":
        return "clash-config.yaml"
    elif format_type == "xray":
        return "xray-config.json"
    elif format_type == "full":
        return "sing-box-config.json"
    elif format_type == "outbound":
        return "sing-box-outbound.json"
    return f"config.{extension}"


@router.post("/convert", response_class=HTMLResponse)
async def convert_form(
    request: Request,
    url: str = Form(...),
    format_type: str = Form(None)
):
    """Обработка формы конвертации"""
    try:
        # Проверяем, является ли это подпиской
        if is_subscription_url(url):
            vpn_links = parse_subscription_sync(url)
            
            if not vpn_links:
                return templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "url": url,
                        "format_type": format_type,
                        "error": "Не удалось извлечь VPN ссылки из подписки",
                        "success": False,
                    }
                )
            
            # Если несколько ссылок - обрабатываем как подписку
            if len(vpn_links) > 1:
                # Если формат не выбран или пустой - показываем опции формата
                if not format_type or format_type == "outbound" or format_type not in ["text", "clash", "singbox", "xray"]:
                    return templates.TemplateResponse(
                        "index.html",
                        {
                            "request": request,
                            "url": url,
                            "format_type": format_type or "clash",
                            "subscription_links": vpn_links,
                            "links_count": len(vpn_links),
                            "show_subscription_formats": True,
                            "success": False,
                        }
                    )
                
                # Конвертируем в зависимости от выбранного формата
                if format_type == "text":
                    # Текстовый файл
                    file_content = "\n".join(vpn_links)
                    return templates.TemplateResponse(
                        "index.html",
                        {
                            "request": request,
                            "url": url,
                            "format_type": format_type,
                            "config": file_content,
                            "config_format": "text",
                            "links_count": len(vpn_links),
                            "success": True,
                        }
                    )
                elif format_type == "clash":
                    # Clash YAML
                    try:
                        config = convert_multiple_to_clash(vpn_links)
                        yaml_config = format_yaml(config)
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "config": yaml_config,
                                "config_format": "yaml",
                                "links_count": len(vpn_links),
                                "success": True,
                            }
                        )
                    except Exception as e:
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "error": f"Ошибка при конвертации в Clash: {str(e)}",
                                "success": False,
                            }
                        )
                elif format_type == "singbox":
                    # sing-box JSON (полная конфигурация)
                    try:
                        outbounds = []
                        for link in vpn_links:
                            try:
                                outbound = VPNLinkParser.to_singbox_outbound(link)
                                outbounds.append(outbound)
                            except Exception:
                                continue
                        
                        if not outbounds:
                            raise ValueError("Не удалось конвертировать ни одну ссылку")
                        
                        config = create_full_config(outbounds)
                        json_config = format_json(config)
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "config": json_config,
                                "config_format": "json",
                                "links_count": len(vpn_links),
                                "success": True,
                            }
                        )
                    except Exception as e:
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "error": f"Ошибка при конвертации в sing-box: {str(e)}",
                                "success": False,
                            }
                        )
                elif format_type == "xray":
                    # Xray Core JSON
                    try:
                        config = convert_multiple_to_xray(vpn_links)
                        json_config = format_xray_json(config)
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "config": json_config,
                                "config_format": "json",
                                "links_count": len(vpn_links),
                                "success": True,
                            }
                        )
                    except Exception as e:
                        return templates.TemplateResponse(
                            "index.html",
                            {
                                "request": request,
                                "url": url,
                                "format_type": format_type,
                                "error": f"Ошибка при конвертации в Xray: {str(e)}",
                                "success": False,
                            }
                        )
            else:
                # Если только одна ссылка, конвертируем её
                url = vpn_links[0]
        
        if format_type == "clash":
            # Конвертация в Clash YAML
            config = convert_to_clash(url)
            yaml_config = format_yaml(config)
            
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "url": url,
                    "format_type": format_type,
                    "config": yaml_config,
                    "config_format": "yaml",
                    "success": True,
                }
            )
        elif format_type == "xray":
            # Конвертация в Xray Core
            config = convert_multiple_to_xray([url])
            json_config = format_xray_json(config)
            
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "url": url,
                    "format_type": format_type,
                    "config": json_config,
                    "config_format": "json",
                    "success": True,
                }
            )
        elif format_type == "singbox":
            # Если выбран singbox, но не указан подтип - показываем выбор
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "url": url,
                    "format_type": format_type,
                    "show_singbox_options": True,
                    "success": False,
                }
            )
        elif format_type in ["full", "outbound"]:
            # Конвертация в sing-box (full или outbound)
            full_config = format_type == "full"
            config = convert_to_singbox(url, full_config=full_config)
            json_config = format_json(config)
            
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "url": url,
                    "format_type": format_type,
                    "config": json_config,
                    "config_format": "json",
                    "success": True,
                }
            )
        else:
            # Если format_type не указан или неизвестен - показываем выбор
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "url": url,
                    "format_type": format_type or "clash",
                    "show_singbox_options": False,
                    "success": False,
                }
            )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "url": url,
                "format_type": format_type,
                "error": str(e),
                "success": False,
            }
        )


@router.post("/api/download")
async def download_config(
    url: str = Form(...),
    format_type: str = Form(...)
):
    """API endpoint для скачивания конфигурации"""
    try:
        # Проверяем, является ли это подпиской
        if is_subscription_url(url):
            vpn_links = parse_subscription_sync(url)
            
            if len(vpn_links) > 1:
                # Подписка
                if format_type == "text":
                    content = "\n".join(vpn_links)
                    filename = generate_filename_from_url(url, "txt")
                    media_type = "text/plain"
                elif format_type == "clash":
                    config = convert_multiple_to_clash(vpn_links)
                    content = format_yaml(config)
                    filename = generate_filename_from_url(url, "yaml")
                    media_type = "application/x-yaml"
                elif format_type == "singbox":
                    outbounds = []
                    for link in vpn_links:
                        try:
                            outbound = VPNLinkParser.to_singbox_outbound(link)
                            outbounds.append(outbound)
                        except Exception:
                            continue
                    if not outbounds:
                        raise ValueError("Не удалось конвертировать ни одну ссылку")
                    config = create_full_config(outbounds)
                    content = format_json(config)
                    filename = generate_filename_from_url(url, "json")
                    media_type = "application/json"
                elif format_type == "xray":
                    config = convert_multiple_to_xray(vpn_links)
                    content = format_xray_json(config)
                    filename = generate_filename_from_url(url, "json")
                    media_type = "application/json"
                else:
                    raise ValueError("Неподдерживаемый формат")
            else:
                url = vpn_links[0] if vpn_links else url
        
        # Одиночная ссылка
        if format_type == "clash":
            config = convert_to_clash(url)
            content = format_yaml(config)
            filename = generate_filename_from_url(url, "yaml", "clash")
            media_type = "application/x-yaml"
        elif format_type == "xray":
            config = convert_multiple_to_xray([url])
            content = format_xray_json(config)
            filename = generate_filename_from_url(url, "json", "xray")
            media_type = "application/json"
        elif format_type == "full":
            config = convert_to_singbox(url, full_config=True)
            content = format_json(config)
            filename = generate_filename_from_url(url, "json", "full")
            media_type = "application/json"
        elif format_type == "outbound":
            config = convert_to_singbox(url, full_config=False)
            content = format_json(config)
            filename = generate_filename_from_url(url, "json", "outbound")
            media_type = "application/json"
        else:
            raise ValueError("Неподдерживаемый формат")
        
        return Response(
            content=content.encode('utf-8'),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

