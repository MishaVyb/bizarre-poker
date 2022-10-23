import React, { useContext } from 'react'
import { Alert, Badge, Button, Card, Col, Container, OverlayTrigger, Popover, Row, Tooltip } from 'react-bootstrap'
import { useLoaderData, useRouteLoaderData } from 'react-router-dom'
import { AuthContext } from '../../context'
import CardsString from '../UI/CardsString'
import CardList from './CardList'
import classes from './Player.module.css'

const Player = ({latest, title, children}) => {
  const player = children
  const {game} = useLoaderData()
  const {auth} = useContext(AuthContext)

  let lastPerformed
  if (latest?.performer == player.user ) {
    lastPerformed =  <Col><Alert variant="info">{latest.message}</Alert></Col>
  }

  const dealTotalAmount = game.config.deal_cards_amounts.reduce(
    (partialSum, a) => partialSum + a,
    0
  )

  const popover = (
    <Popover id="popover-basic">
      <Popover.Header as="h3">{player.combo?.kind} by thouse cards</Popover.Header>
      <Popover.Body>
        <CardsString>{player.combo?.chain}</CardsString>
      </Popover.Body>
    </Popover>
  )

  return (
    <Card className={player.is_performer ? classes.performerCard : classes.notPerformerCard}>

      {/* ---------- name and host / dealer --------- */}
      <Card.Title className={player.is_performer ? 'text-white' : ''}>
        <Row>
          {player.is_host
            ? (
              <OverlayTrigger placement="bottom" overlay={
                <Tooltip id={'tooltip-is-host'}>
                  host user
                </Tooltip>
              }
              >
                <Col>
                  {'👑'}
                </Col>
              </OverlayTrigger>
            )
            : <Col></Col>
          }
          <Col md="auto">
            {title ? title : player.user}
          </Col>
          {player.is_dealer
            ? (
              <OverlayTrigger placement="bottom" overlay={
                <Tooltip id={'tooltip-is-host'}>
                  dealer player
                </Tooltip>
              }
              >
                <Col>
                  {'🎩'}
                </Col>
              </OverlayTrigger>
            )
            :<Col></Col>
          }
        </Row>

      </Card.Title>

      {/* ---------- hand --------- */}
      <CardList amount={dealTotalAmount}>{player.hand}</CardList>

      <Card.Footer>
        <Row>
          {/* ------- profile_bank --------- */}
          <Col><Badge bg="light" text="dark"><strong>{''}{player.profile_bank}{' $'}</strong></Badge></Col>

          {/* ---------- combo ------------- */}
          {player.combo
            ? (
              <Col md="auto">
                <OverlayTrigger trigger="click" placement="right" overlay={popover}>
                  <Button variant="danger" size="sm" text=''><strong>{''}{player.combo?.kind}</strong></Button>
                </OverlayTrigger>
              </Col>
            )
            : <></>
          }

          {/* ---------- bet_total --------- */}
          {player.bets.length
            ? (
              <OverlayTrigger placement="bottom" overlay={
                <Tooltip id={'tooltip'}>
                  sum all of bets for this stage
                </Tooltip>
              }
              >
                <Col><Badge bg="success" ><strong>{player.bet_total}{' $'}</strong></Badge></Col>
              </OverlayTrigger>
            )
            : <></>
          }
        </Row>

        {/* ---------- last player action --------- */}
        <Row>
          {lastPerformed}
        </Row>
      </Card.Footer>

    </Card>
  )
}

export default Player