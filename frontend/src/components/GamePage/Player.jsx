import React from 'react'
import { Alert, Badge, Card, Col, Container, Row } from 'react-bootstrap'
import { useLoaderData, useRouteLoaderData } from 'react-router-dom'
import CardList from './CardList'
import classes from './Player.module.css'

const Player = ({children}) => {
  const player = children
  const {game} = useLoaderData()

  let action
  for (let i = game.actions_history.length - 1; i >= 0; i--) {
    action = game.actions_history[i]
    if (action.performer == player.user) {
      break
    }
  }

  return (
    <Card className={player.is_performer ? classes.performerCard : classes.notPerformerCard}>

      {/* ---------- name --------- */}
      <Card.Title className={player.is_performer ? 'text-white' : ''}>
        {player.user}
      </Card.Title>

      {/* ---------- hand --------- */}
      <CardList amount={game.config.deal_cards_amount}>{player.hand}</CardList>

      <Card.Footer>
        <Row>
          {/* ------- profile_bank --------- */}
          <Col><Badge bg="light" text="dark"><strong>{''}{player.profile_bank}{'$'}</strong></Badge></Col>

          {/* ---------- combo ------------- */}
          {player.combo
            ? <Col><Badge bg="danger" text=''><strong>{''}{player.combo?.kind}</strong></Badge></Col>
            : <></>
          }

          {/* ---------- bet_total --------- */}
          {player.bets.length
            ? <Col><Badge bg="success" ><strong>{''}{player.bet_total}</strong></Badge></Col>
            : <></>
          }
        </Row>

        {/* ---------- action history --------- */}
        <Row>
          <Col><Alert variant="info">{action?.message}</Alert></Col>
        </Row>
      </Card.Footer>

    </Card>
  )
}

export default Player