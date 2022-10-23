import React, { useContext, useState } from 'react'
import { Badge, Col, Row } from 'react-bootstrap'
import Button from 'react-bootstrap/Button'
import Offcanvas from 'react-bootstrap/Offcanvas'
import { useLoaderData } from 'react-router-dom'
import { AuthContext } from '../../context'
import Loader from './Loader'


const OffcanvasHistory = ({...props}) => {
  const [show, setShow] = useState(false)
  const {auth} = useContext(AuthContext)

  const handleClose = () => setShow(false)
  const handleShow = () => setShow(true)

  const { game }= useLoaderData()


  const actionsComonents = game.actions_history.map((action, i) => {
    let bg = action.performer ? 'secondary' : 'light'
    if (action.performer && action.performer == auth.username) {
      bg = 'primary'
    }
    return <Row key={i}><Badge bg={bg}><h5>{action.message}</h5></Badge></Row>
  })


  return (
    <Col>
      <Button variant="outline-primary" onClick={handleShow} className="me-2">
        history
      </Button>
      <Offcanvas show={show} onHide={handleClose} {...props}>
        <Offcanvas.Header closeButton>
          <Offcanvas.Title></Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          {actionsComonents}
        </Offcanvas.Body>
      </Offcanvas>
    </Col>
  )
}

export default OffcanvasHistory