"""Ponte WSGI para o Passenger (cPanel/HostGator) rodar o app FastAPI (ASGI).

Necessário porque o Passenger, no cPanel Setup Python App, só sabe invocar
uma aplicação WSGI (variável `application`) — o a2wsgi adapta o FastAPI para
esse contrato sem alterar app.py.
"""
from a2wsgi import ASGIMiddleware

from app import app as _fastapi_app

application = ASGIMiddleware(_fastapi_app)
