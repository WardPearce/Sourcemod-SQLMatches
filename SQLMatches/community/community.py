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

from typing import AsyncGenerator, List
from uuid import uuid4
from datetime import datetime
from secrets import token_urlsafe

from sqlalchemy.sql import select, and_, or_, func

from ..resources import Sessions, Config, DemoQueue

from ..tables import (
    community_table,
    scoreboard_total_table,
    scoreboard_table,
    user_table,
    api_key_table,
    statistic_table
)

from ..exceptions import (
    InvalidCommunity,
    InvalidSteamID
)
from .models import (
    CommunityModel,
    MatchModel,
    ProfileModel,
    CommunityStatsModel
)
from .match import Match


class Community:
    def __init__(self, community_name: str) -> str:
        """Handles community interactions.

        Paramters
        ---------
        community_name: str
            ID of community.
        """

        self.community_name = community_name

    async def stats(self) -> CommunityStatsModel:
        """Gets basic stats about community.

        Returns
        -------
        CommunityStatsModel
        """

        sub_active_matches = select([
            func.count().label("active_matches")
        ]).select_from(
            scoreboard_total_table
        ).where(
            and_(
                scoreboard_total_table.c.community_name == self.community_name,
                scoreboard_total_table.c.status == 1
            )
        ).alias("sub_active_matches")

        sub_stored_demos = select([
            func.count().label("stored_demos")
        ]).select_from(
            scoreboard_total_table
        ).where(
            and_(
                scoreboard_total_table.c.community_name == self.community_name,
                scoreboard_total_table.c.demo_status == 2
            )
        ).alias("sub_stored_demos")

        sub_total_matches = select([
            func.count().label("total_matches"),
        ]).select_from(
            scoreboard_total_table
        ).where(
            and_(
                scoreboard_total_table.c.community_name == self.community_name,
                scoreboard_total_table.c.status == 0
            )
        ).alias("sub_total_matches")

        query = select([
            func.count().label("total_users"),
            sub_active_matches.c.active_matches,
            sub_stored_demos.c.stored_demos,
            sub_total_matches.c.total_matches
        ]).select_from(
            statistic_table
        ).where(
            statistic_table.c.community_name == self.community_name
        )

        return CommunityStatsModel(
            await Sessions.database.fetch_one(query)
        )

    async def profile(self, steam_id: str) -> ProfileModel:
        """Get user profile.

        Parameters
        ----------
        steam_id : str

        Returns
        -------
        ProfileModel

        Raises
        ------
        InvalidSteamID
        """

        query = select([
            user_table.c.name,
            user_table.c.timestamp,
            statistic_table.c.steam_id,
            statistic_table.c.kills,
            statistic_table.c.headshots,
            statistic_table.c.assists,
            statistic_table.c.deaths,
            statistic_table.c.shots_fired,
            statistic_table.c.shots_hit,
            statistic_table.c.mvps
        ]).select_from(
            statistic_table.join(
                user_table,
                user_table.c.steam_id == statistic_table.c.steam_id
            )
        ).where(
            and_(
                statistic_table.c.steam_id == steam_id,
                statistic_table.c.community_name == self.community_name
            )
        )

        row = await Sessions.database.fetch_one(query=query)
        if row:
            return ProfileModel(row)
        else:
            raise InvalidSteamID()

    async def delete_matches(self, matches: List[str]) -> None:
        """Used to bulk delete matches.

        Parameters
        ----------
        matches : List[str]
            List of match IDs to delete.
        """

        query = scoreboard_total_table.delete().where(
            scoreboard_total_table.c.match_id == scoreboard_table.c.match_id
        ).where(
            and_(
                scoreboard_total_table.c.community_name == self.community_name,
                scoreboard_total_table.c.match_id.in_(matches)
            )
        )

        await Sessions.database.execute(query)

        # Todo
        # Work out sqlalchemy left joining delete,
        # so i don't need this ugly mess.
        await Sessions.database.execute(
            scoreboard_total_table.delete().where(
                and_(
                    scoreboard_total_table.c.community_name
                    == self.community_name,
                    scoreboard_total_table.c.match_id.in_(matches)
                )
            )
        )

        if Config.upload_type is not None:
            DemoQueue.matches.append(matches)

    async def create_match(self, team_1_name: str, team_2_name: str,
                           team_1_side: int, team_2_side: int,
                           team_1_score: int, team_2_score: int,
                           map_name: str) -> Match:
        """Creates a match.

        Returns
        -------
        Match
            Used for interacting with matches.
        """

        match_id = str(uuid4())

        query = scoreboard_total_table.insert().values(
            match_id=match_id,
            team_1_name=team_1_name,
            team_2_name=team_2_name,
            team_1_side=team_1_side,
            team_2_side=team_2_side,
            map=map_name,
            community_name=self.community_name,
            team_1_score=team_1_score,
            team_2_score=team_2_score,
            status=1,
            demo_status=0,
            timestamp=datetime.now()
        )

        await Sessions.database.execute(query=query)

        return self.match(match_id)

    def match(self, match_id) -> Match:
        """Handles interactions with a match

        Paramters
        ---------
        match_id: str
            ID of match
        """

        return Match(match_id, self.community_name)

    async def regenerate(self, old_key: str) -> str:
        """Regenerates a API key.

        Parameters
        ----------
        old_key : str
            Old key to update.
        """

        key = token_urlsafe(24)

        query = api_key_table.update().values(
            api_key=key,
            timestamp=datetime.now()
        ).where(
            and_(
                api_key_table.c.community_name == self.community_name,
                api_key_table.c.api_key == old_key
            )
        )

        await Sessions.database.execute(query=query)

        return key

    async def regenerate_master(self) -> str:
        """Regenerates the master API key.
        """

        key = token_urlsafe(24)

        query = api_key_table.update().values(
            api_key=key,
            timestamp=datetime.now()
        ).where(
            and_(
                api_key_table.c.community_name == self.community_name,
                api_key_table.c.master == 1
            )
        )

        await Sessions.database.execute(query=query)

        return key

    async def exists(self) -> bool:
        """Checks if community exists with name.
        """

        query = select([func.count()]).select_from(community_table).where(
            community_table.c.community_name == self.community_name
        )

        return await Sessions.database.fetch_val(query=query) > 0

    async def matches(self, search: str = None,
                      page: int = 1, limit: int = 5, desc: bool = True,
                      require_scoreboard: bool = True
                      ) -> AsyncGenerator[MatchModel, Match]:
        """Lists matches.

        Paramters
        ---------
        search: str
        page: int
        limit: int
        desc: bool, optional
            by default True
        require_scoreboard : bool, optional
            If enabled scoreboard will need to be ready
            to pull match, by default True

        Yields
        ------
        MatchModel
            Holds basic match details.
        Match
            Used for interacting with a match.
        """

        query = select([
            scoreboard_total_table.c.match_id,
            scoreboard_total_table.c.timestamp,
            scoreboard_total_table.c.status,
            scoreboard_total_table.c.demo_status,
            scoreboard_total_table.c.map,
            scoreboard_total_table.c.team_1_name,
            scoreboard_total_table.c.team_2_name,
            scoreboard_total_table.c.team_1_score,
            scoreboard_total_table.c.team_2_score,
            scoreboard_total_table.c.team_1_side,
            scoreboard_total_table.c.team_2_side,
            scoreboard_total_table.c.community_name
        ])

        if search:
            like_search = "%{}%".format(search)

            query = query.select_from(
                scoreboard_total_table.join(
                    scoreboard_table,
                    scoreboard_table.c.match_id ==
                    scoreboard_total_table.c.match_id
                ).join(
                    user_table,
                    user_table.c.steam_id == scoreboard_table.c.steam_id
                )
            ).where(
                and_(
                    scoreboard_total_table.c.community_name ==
                    self.community_name,
                    or_(
                        scoreboard_total_table.c.match_id == search,
                        scoreboard_total_table.c.map.like(like_search),
                        scoreboard_total_table.c.team_1_name.like(
                            like_search),
                        scoreboard_total_table.c.team_2_name.like(
                            like_search),
                        user_table.c.name.like(like_search),
                        user_table.c.steam_id == search
                    )
                )
            ).distinct()
        elif require_scoreboard:
            query = query.select_from(
                scoreboard_total_table.join(
                    scoreboard_table,
                    scoreboard_table.c.match_id ==
                    scoreboard_total_table.c.match_id
                )
            ).where(
                scoreboard_total_table.c.community_name
                == self.community_name,
            ).distinct()
        else:
            query = query.select_from(
                scoreboard_total_table
            ).where(
                scoreboard_total_table.c.community_name
                == self.community_name,
            )

        query = query.order_by(
            scoreboard_total_table.c.timestamp.desc() if desc
            else scoreboard_total_table.c.timestamp.asc()
        ).limit(limit).offset((page - 1) * limit if page > 1 else 0)

        async for row in Sessions.database.iterate(query=query):
            yield MatchModel(row), self.match(row["match_id"])

    async def get(self) -> CommunityModel:
        """Gets base community details.

        Returns
        -------
        CommunityModel
            Holds community data.

        Raises
        ------
        InvalidCommunity
            Raised when community ID doesn't exist.
        """

        query = select([
            api_key_table.c.api_key,
            api_key_table.c.owner_id,
            community_table.c.disabled,
            community_table.c.community_name,
            community_table.c.timestamp
        ]).select_from(
            community_table.join(
                api_key_table,
                community_table.c.community_name ==
                api_key_table.c.community_name
            )
        ).where(
            and_(
                community_table.c.community_name == self.community_name,
                api_key_table.c.master == 1
            )
        )

        row = await Sessions.database.fetch_one(query=query)
        if row:
            return CommunityModel(row)
        else:
            raise InvalidCommunity()

    async def disable(self) -> None:
        """Disables a community.
        """

        query = community_table.update().where(
            community_table.c.community_name == self.community_name
        ).values(disabled=True)

        await Sessions.database.execute(query=query)