import React from "react";
import { useLoaderData } from "react-router-dom";
import GameList from "../components/GameList";

const GameListPage = () => {
  const games = useLoaderData();
  return (
    <div>
      <GameList games={games} />
    </div>
  );
};

export default GameListPage;
