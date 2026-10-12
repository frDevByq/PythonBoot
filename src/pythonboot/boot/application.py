"""FastAPI 应用工厂，后续在此接入容器与自动配置。"""

from fastapi import FastAPI


def create_app(*, title: str = "PythonBoot", version: str = "0.1.0") -> FastAPI:
    """创建独立的应用实例。"""
    return FastAPI(title=title, version=version)
