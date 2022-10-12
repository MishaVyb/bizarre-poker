import React from 'react'
import { Alert, Container, Row } from 'react-bootstrap'
import { useLoaderData } from 'react-router-dom'
import Actions from '../components/GamePage/Actions'
import Bank from '../components/GamePage/Bank'
import Flop from '../components/GamePage/Flop'
import Player from '../components/GamePage/Player'
import Loader from '../components/UI/Loader'

const GamePage = () => {
  const data = useLoaderData()
  if (!data){
    return (<Loader/>)
  }

  const {game, playerMe, playersOther, actions} = data
  console.log(game)
  console.log(playersOther)


  const pp = playersOther.map((player) => {
    return (<Player key={player.user}>{player}</Player>)
  })
  console.log(pp)

  return (
    <Container className={'text-center'} >
      <Alert variant='info'>{game.status}</Alert>

      <Actions actions={actions}/>
      <Flop>{game.table}</Flop>
      <Bank>{game.bank}</Bank>

      <Row className='d-flex justify-content-center'>
        <Player>{playerMe}</Player>
      </Row>
      <Row className='d-flex justify-content-center'>{pp}</Row>

    </Container>
  )
}

export default GamePage