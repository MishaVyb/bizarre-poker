import React, { useContext, useState } from 'react'
import { Badge, Col, OverlayTrigger, Row, Tooltip } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import Offcanvas from 'react-bootstrap/Offcanvas'
import { useLoaderData, useSubmit } from 'react-router-dom'
import { AuthContext } from '../../context'
import Loader from './Loader'


const OffcanvasPlayers = ({...props}) => {
  const [show, setShow] = useState(false)
  const {gameService} = useContext(AuthContext)
  const submit = useSubmit()

  const handleClose = () => setShow(false)
  const handleShow = () => setShow(true)

  const { game, playerMe, playersAll, actions } = useLoaderData()



  let lastPosition
  const playersComonents = playersAll.map((player) => {
    const handleKick = async () => {
      await gameService.kick(game.id, player.user)
      submit()
    }

    lastPosition = player.position  // [todo] need refactoring
    let button
    if (playerMe.is_host) {

      const isDisabled = !actions.kick?.available
      button = (
        <OverlayTrigger
          placement="end"
          overlay={
            <Tooltip id={'tooltip-fdsa'}>

            </Tooltip>
          }
        >
          <Button variant="outline-danger" onClick={handleKick} disabled={isDisabled}>
          kick out
          </Button>
        </OverlayTrigger>
      )
    }
    return (
      <Row key={player.user}>
        <Col>
          <Badge bg='light'><h5>{player.position}</h5></Badge>
        </Col>
        <Col>
          <Badge bg='light'><h5>{player.user}</h5></Badge>
        </Col>
        <Col md="auto">
          {button}
        </Col>
      </Row>
    )
  })


  const preplayersComonents = game.players_preforms.map((preplayer, i) => {
    const handleKick = async () => {
      const response = await gameService.approveJoin(game.id, preplayer)
      submit()
    }

    let button
    if (playerMe.is_host) {
      button = (
        <Button variant="outline-danger" onClick={handleKick}>
          join
        </Button>
      )
    }

    return (
      <Row key={preplayer}>
        <Col>
          <Badge bg='light'><h5>{lastPosition + i}</h5></Badge>
        </Col>
        <Col>
          <Badge bg='light'><h5>{preplayer}</h5></Badge>
        </Col>
        <Col md="auto">
          {button}
        </Col>
      </Row>
    )
  })


  return (
    <Col>
      <Button variant="outline-primary" onClick={handleShow} className="me-2">
        players
      </Button>
      <Offcanvas show={show} onHide={handleClose} {...props}>
        <Offcanvas.Header closeButton>
        </Offcanvas.Header>
        <Offcanvas.Body>
          <Offcanvas.Title>in game</Offcanvas.Title>
          {playersComonents}
          <Offcanvas.Title>{preplayersComonents.length ? 'waiting for approval' : ''}</Offcanvas.Title>
          {preplayersComonents}
        </Offcanvas.Body>
      </Offcanvas>
    </Col>
  )
}

export default OffcanvasPlayers