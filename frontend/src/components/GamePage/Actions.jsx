import React, { useContext } from 'react'
import { Button, Col, Container, Row } from 'react-bootstrap'
import { AuthContext } from '../../context'

const Actions = (  { actions }) => {
  const { gameService } = useContext(AuthContext)

  const buttons = actions.map((action) => {
    return (
      <Button key={action.name} onClick={()=> {gameService.post(action.url)}}>
        {action.name}
      </Button>
    )
  })
  return (
    <Row>
      <Col>{buttons}</Col>
    </Row>
  )
}

export default Actions
