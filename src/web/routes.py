"""Роуты для веб-сайта"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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


@router.post("/convert", response_class=HTMLResponse)
async def convert_form(
    request: Request,
    url: str = Form(...),
    format_type: str = Form("outbound")
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
                    # Показываем список ссылок для выбора формата
                    return templates.TemplateResponse(
                        "index.html",
                        {
                            "request": request,
                            "url": url,
                            "format_type": format_type,
                            "subscription_links": vpn_links,
                            "links_count": len(vpn_links),
                            "success": True,
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
        else:
            # Конвертация в sing-box
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

