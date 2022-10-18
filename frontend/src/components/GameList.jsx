import React from 'react'
import { Stack } from 'react-bootstrap'
import GameItem from './GameItem'

const GameList = ({ games }) => {
  if (!games) {
    return <h4>No games</h4>
  }

  const gameItems = games.map((game) => <GameItem game={game} key={game.id} />)
  return <Stack gap={1}>{gameItems}</Stack>
}

export default GameList
