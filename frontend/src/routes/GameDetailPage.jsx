import { React, useContext, useEffect, useState } from 'react'
import { Alert, Badge, Button, ButtonGroup, Col, Container, Offcanvas, OverlayTrigger, Row, Tooltip } from 'react-bootstrap'
import { useLoaderData, useNavigate, useSubmit } from 'react-router-dom'

import CardList from '../components/GamePage/CardList'
import Player from '../components/GamePage/Player'
import Loader from '../components/UI/Loader'
import ControlPanel from '../components/GamePage/ControlPanel'
import OffcanvasHistory from '../components/UI/OffcanvasHistory'
import OffcanvasPlayers from '../components/UI/OffcanvasPlayers'
import GameService from '../services/GameService'
import { AuthContext, ErrorContext } from '../context'

const GamePage = () => {
  const data = useLoaderData()
  const {gameService} = useContext(AuthContext)
  const {setError} = useContext(ErrorContext)
  const navigate = useNavigate()

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
    const id = setInterval(submit, 2500)
    return () => {
      clearInterval(id)
    }
  }, [])
  //---------------------------------------

  let notEnoughPlayers
  if (game.players.length == 1) {
    notEnoughPlayers = (<Alert variant="danger">you can not play by 1 player! <strong>join somebody</strong></Alert>)
  }
  let notEnoughMoney
  for (let i = 0; i < playersOther.length; i++) {
    const player = playersOther[i]
    if (player.profile_bank < game.config.big_blind) {
      notEnoughMoney = (<Alert variant="danger"><strong>{player.user}</strong> does not have enough money! <strong>kick him out</strong></Alert>)
    }
  }

  let latestStageAction
  let latestPlayerAction
  let action
  for (let i = game.actions_history.length - 1; i >= 0; i--) {
    action = game.actions_history[i]
    if (!latestStageAction && !action.performer) {
      latestStageAction = <Alert variant="info">{action.message}</Alert>
    }
    if (!latestPlayerAction && action.performer) {
      latestPlayerAction = action
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
        {notEnoughPlayers ? (<Col>{notEnoughPlayers}</Col>) : <></>}
        {notEnoughMoney ? (<Col>{notEnoughMoney}</Col>) : <></>}
        {latestStageAction ? (<Col>{latestStageAction}</Col>) : <></>}

        <Col>
          <Alert variant="info">{game.stage.status}</Alert>
        </Col>
      </Row>

      {/* ------------ second info panel -------------- */}
      <Row>
        <Col>
          <ButtonGroup>
            <OffcanvasPlayers placement="start"/>
            <Button variant='outline-danger' onClick={()=>{

              gameService.leave(game.id, playerMe.user).catch((error)=>{setError(error)})
              navigate('/')


            }}>
              leave game
            </Button>
          </ButtonGroup>
        </Col>

        <Col>
          <ButtonGroup>
            <OverlayTrigger placement="bottom" overlay={
              <Tooltip id={'tooltip'}>
                game style
              </Tooltip>
            }
            >
              <Button variant="outline-primary"><h6>{game.config.name}</h6></Button>
            </OverlayTrigger>
            <OverlayTrigger placement="bottom" overlay={
              <Tooltip id={'tooltip'}>
                round bank
              </Tooltip>
            }
            >
              <Button variant="primary"><h6>{game.bank_total}</h6></Button>
            </OverlayTrigger>
          </ButtonGroup>
        </Col>
        <OffcanvasHistory placement="end"/>
      </Row>



      {/* ------------ flop -------------- */}
      <CardList amount={flopsTotalAmount}>{game.table}</CardList>{' '}

      {/* ------------ control -------------- */}
      <ControlPanel game={game}>{actions}</ControlPanel>

      {/* ------------ all players -------------- */}
      <Row className="d-flex justify-content-center">
        <Col md={4}>
          <Player latest={latestPlayerAction} title={'your hand'}>{playerMe}</Player>
        </Col>
        {playersOther.map((player) => {
          return (
            <Col key={player.user}>
              <Player latest={latestPlayerAction}>{player}</Player>
            </Col>
          )
        })}
      </Row>

    </Container>
  )
}

export default GamePage
