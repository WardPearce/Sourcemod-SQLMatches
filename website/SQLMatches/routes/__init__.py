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


from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from .home import HomePage
from .community import CommunityPage
from .scoreboard import ScoreboardPage

from .steam import SteamLogin, SteamValidate

from ..resources import Config


ROUTES = [
    Route("/", HomePage, name="HomePage"),
    Mount("/login", routes=[
        Route("/steam", SteamLogin, name="SteamLogin"),
        Route("/validate", SteamValidate)
    ]),
    Mount("/assets", StaticFiles(directory=Config.assets_dir), name="assets"),
    Mount("/{community}", routes=[
        Route("/", CommunityPage),
        Route("/{scoreboard_id}", ScoreboardPage)
    ]),
]