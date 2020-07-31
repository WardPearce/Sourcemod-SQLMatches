# -*- coding: utf-8 -*-

"""
GNU General Public License v3.0 (GPL v3)
Copyright (c) 2020-2020 WardPearce
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""


from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from secrets import token_urlsafe

from databases import Database
from aiohttp import ClientSession

from .tables import create_tables
from .resources import Sessions, Config
from .settings import DatabaseSettings
from .routes import ROUTES


__version__ = "0.0.1"


class SQLMatches(Starlette):
    def __init__(self, database_settings: DatabaseSettings,
                 friendly_url: str,
                 secret_key: str = token_urlsafe(),
                 **kwargs) -> None:
        """
        SQLMatches server.

        database_settings: DatabaseSettings
            Holds settings for database.
        friendly_url: str
            URL to project.
        secret_key: str
            Optionally pass your own url safe secret key.
        """

        startup_tasks = [self._startup]
        shutdown_tasks = [self._shutdown]

        if "on_startup" in kwargs:
            startup_tasks = startup_tasks + kwargs["on_startup"]

        if "on_shutdown" in kwargs:
            shutdown_tasks = shutdown_tasks + kwargs["on_shutdown"]

        middlewares = []
        if "middleware" in kwargs:
            middlewares = kwargs["middleware"]

        middlewares.append(
            Middleware(SessionMiddleware, secret_key=secret_key)
        )

        if "routes" in kwargs:
            routes = kwargs["routes"] + ROUTES
        else:
            routes = ROUTES

        if friendly_url[:1] != "/":
            friendly_url += "/"

        Config.url = friendly_url

        database_url = "://{}:{}@{}:{}/{}?charset=utf8mb4".format(
            database_settings.username,
            database_settings.password,
            database_settings.server,
            database_settings.port,
            database_settings.database
        )

        Sessions.database = Database(
            database_settings.engine + database_url
        )

        create_tables(
            "{}+{}{}".format(
                database_settings.engine,
                database_settings.alchemy_engine,
                database_url
            )
        )

        Starlette.__init__(
            self,
            routes=routes,
            middleware=middlewares,
            on_startup=startup_tasks,
            on_shutdown=shutdown_tasks,
            **kwargs
        )

    async def _startup(self) -> None:
        """
        Starts up needed sessions.
        """

        await Sessions.database.connect()
        Sessions.aiohttp = ClientSession()

    async def _shutdown(self) -> None:
        """
        Closes any underlying sessions.
        """

        await Sessions.database.disconnect()
        await Sessions.aiohttp.close()
