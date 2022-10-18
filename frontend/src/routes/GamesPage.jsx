import React from 'react'
import { useLoaderData } from 'react-router-dom'
import GameList from '../components/GameList'

const GameListPage = () => {
  const games = useLoaderData()
  return <GameList games={games} />
}

export default GameListPage
