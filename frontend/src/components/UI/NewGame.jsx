import React, { useContext, useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, Col, Container, Form, Modal, Row } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { AuthContext, ErrorContext } from '../../context'
import useLoadingWrapper from '../../hooks/useLoadingWrapper'
import Loader from './Loader'





const NewGame = ({show, setShow}) => {
  const handleClose = () => setShow(false)

  const [value, setValue] = useState(0)
  const [choices, setChoices] = useState([])
  const {auth, gameService} = useContext(AuthContext)
  const {setError} = useContext(ErrorContext)
  const navigate = useNavigate()



  const [getChoices, loadingChoices] = useLoadingWrapper(async () => {
    setChoices(await gameService.getCreateChoices())
  })

  useEffect(()=>{
    if (show && auth?.username) {
      getChoices()
    } else if (show && !auth) {
      navigate('/login')
    }
  }, [show])

  const choicesItems = choices.map((choice, index) => {
    return (
      <Col key={choice.value}>
        <Badge  bg={index == value ? 'danger' : 'light'}>
          <strong>{choice.display_name}</strong>
        </Badge>
      </Col>
    )
  })
  const [performCreation, loadingCreations] = useLoadingWrapper(async () => {
    const config = choices[value].value
    let newGame
    newGame = await gameService.create(config).catch((error) => {setError(error)})
    if (newGame) {
      navigate(`/games/${newGame.id}/`)
    } else {
      setShow(false)
    }

  })


  const createSubmit = async (event) => {
    event.preventDefault()
    console.log('createSubmit -> performCreation')
    performCreation()
  }



  return (
    <Modal show={show} onHide={handleClose}>
      <Modal.Header closeButton>
        <Modal.Title>choose game style</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Container>
            <Row>
              <Col>
                {loadingChoices
                  ? <Loader/>
                  : <Form.Range
                    type="range" className="form-range"
                    placeholder={value}
                    value={value}
                    onChange={(event)=>{
                      setValue(event.target.value)
                    }}
                    min={0} max={choices.length-1}
                    step={1}
                    id="configRange"
                  />
                }
              </Col>
            </Row>
            <Row>
              {choicesItems}
            </Row>
          </Container>
        </Form>
      </Modal.Body>
      <Modal.Footer >

        <Container className="">
          <Row>
            <Button variant="primary-outline" onClick={handleClose}>
            close
            </Button>
            <Button
              variant="primary" type="submit"
              disabled={loadingCreations}
              onClick={
                createSubmit

              }
            >
              <h5>{loadingCreations ? 'loading…' : 'create'}</h5>
            </Button>
          </Row>
        </Container>
      </Modal.Footer>
    </Modal>
  )
}

export default NewGame