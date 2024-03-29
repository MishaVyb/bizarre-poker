import React, { useEffect, useState } from 'react'
import { Button, Col, Container, Row } from 'react-bootstrap'
import { useLoaderData, useSubmit } from 'react-router-dom'
import GameList from '../components/GameList'
import NewGame from '../components/UI/NewGame'

const GameListPage = () => {
  const [show, setShow] = useState(false)
  const handleShow = () => setShow(true)
  const games = useLoaderData()


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


  return (
    <Container>
      <Row>
        <Col md={'auto'}>
          <Button variant="danger" onClick={handleShow}>
          new game
          </Button>
        </Col>

        <NewGame show={show} setShow={setShow}></NewGame>
      </Row>
      <Row>
        <GameList games={games} />
      </Row>
    </Container>

  )
}

export default GameListPage
