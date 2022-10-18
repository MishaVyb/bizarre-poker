import { React, useEffect } from 'react'
import { Alert, Badge, Col, Container, Row } from 'react-bootstrap'
import { useLoaderData, useSubmit } from 'react-router-dom'

import CardList from '../components/GamePage/CardList'
import Player from '../components/GamePage/Player'
import Loader from '../components/UI/Loader'
import ControlPanel from '../components/GamePage/ControlPanel'

const GamePage = () => {
  const data = useLoaderData()
  if (!data) {
    return <Loader />
  }
  const { game, playerMe, playersOther, actions } = data

  //------------- AUTO RELOADER ----------
  // we are making fake post request to the same page every 2 sec
  // react-router-dom handle this faky submit action in router 'action' attribute
  // and then re-load loader
  const submit = useSubmit()
  useEffect(() => {
    const id = setInterval(submit, 1000)
    return () => {
      clearInterval(id)
    }
  }, [])
  //---------------------------------------

  let latestStageAction
  let latestPlayerAction
  let action
  for (let i = game.actions_history.length - 1; i >= 0; i--) {
    action = game.actions_history[i]
    if (!latestStageAction && !action.performer) {
      latestStageAction = action.message
    }
    if (!latestPlayerAction && action.performer) {
      latestPlayerAction = action.message
    }
    if (latestStageAction && latestPlayerAction) {break}
  }

  const flopsTotalAmount = game.config.flops_amounts.reduce(
    (partialSum, a) => partialSum + a,
    0
  )

  return (
    <Container className={'text-center'}>
      {/* ------------ info panel -------------- */}
      <Row>
        <Col>
          <Alert variant="info">{latestStageAction}</Alert>
        </Col>
        <Col md={3}>
          <Badge><h5>{'game bank'}</h5><h3>{game.bank}</h3></Badge>
        </Col>
        <Col>
          <Alert variant="info">{game.stage.status}</Alert>
        </Col>
      </Row>

      {/* ------------ flop -------------- */}
      <CardList amount={flopsTotalAmount}>{game.table}</CardList>{' '}

      {/* ------------ control -------------- */}
      <ControlPanel game={game}>{actions}</ControlPanel>

      {/* ------------ all players -------------- */}
      <Row className="d-flex justify-content-center">
        <Col md={4}>
          <Player>{playerMe}</Player>
        </Col>
        {playersOther.map((player) => {
          return (
            <Col key={player.user}>
              <Player>{player}</Player>
            </Col>
          )
        })}
      </Row>

    </Container>
  )
}

export default GamePage
