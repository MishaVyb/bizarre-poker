import React, { useContext, useEffect, useState } from 'react'
import { Badge, Button, Card, Col, Row } from 'react-bootstrap'
import { Link, redirect, useNavigate, useSubmit } from 'react-router-dom'
import { AuthContext } from '../context'


const GameItem = ({ game }) => {
  const { auth, gameService } = useContext(AuthContext)
  const navigate = useNavigate()
  // const [buttonProps, setButtonProps] = useState({})
  const submit = useSubmit()


  let buttonProps = {}
  if (game.players.includes(auth?.username)) {
    buttonProps = {
      title: 'continue',
      variant: 'primary',
      onClick: () => {navigate(`/games/${game.id}/`)}
    }

  } else if (game.players_preforms.includes(auth?.username)) {
    buttonProps = {
      variant: 'light',
      title: 'wait for approval',
      disabled: true
    }
  } else {
    buttonProps = {
      title: 'join',
      variant: 'outline-primary',
      onClick: () => {
        if (!auth?.username) {
          navigate('login')
        } else {
          gameService.join(game.id)
          submit()
        }
      }
    }
  }


  return (
    <Card>
      <Card.Body>
        <Row>
          <Col>
            <h3>{game.id}</h3>
          </Col>

          <Col>
            <Badge bg='light'>
              <h4 className="text-danger">{game.config.name}
                <small className="text-muted"> style</small>
              </h4>
            </Badge>
          </Col>
          <Col>
            <Badge bg='light'>
              <h4>{game.players.length}
                <small className="text-muted"> players</small>
              </h4>
            </Badge>
          </Col>
          <Col>

            <Button
              variant={buttonProps.variant}
              size="sm"
              onClick={buttonProps.onClick}
              disabled={buttonProps.disabled}
            >

              {buttonProps.title}
            </Button>


          </Col>
        </Row>
      </Card.Body>
    </Card>
  )
}

export default GameItem
