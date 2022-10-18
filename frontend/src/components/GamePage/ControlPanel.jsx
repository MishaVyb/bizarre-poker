import React, { useContext, useMemo, useState } from 'react'
import { Button, ButtonGroup, Col, Row  } from 'react-bootstrap'
import {Form as BootsrtrapForm }  from 'react-bootstrap'
import { Form, useLoaderData} from 'react-router-dom'
import { AuthContext } from '../../context'


const ControlPanel = ({ children}) => {
  // children -- list of awaliable actions

  const actions = children
  const {game} = useLoaderData()
  const {gameService} = useContext(AuthContext)
  const [betValue, setBetValue] = useState(actions.bet?.values?.min)


  const getButtons = ()=>{
    let buttons = []
    for (const [name, action] of Object.entries(actions)) {
      const valueElement = (name === 'bet' && action.available
        ? <strong>{betValue}{'$ '}</strong>
        : <></>
      )

      const variant = (action.available
        ? 'primary'
        : 'outline-primary'
      )
      buttons.push(
        (
          <Button type='submit' variant={variant} key={name} disabled={!action.available}
            onClick={()=> {
              // pass betValue as POST data to every actions
              // but it will take affect only on bet action,
              // other action will ignore data on server side
              gameService.post(action.url, {value: betValue})
            }}
          >
            {valueElement}{name}
          </Button>)
      )
    }
    return buttons
  }

  const buttons = useMemo(getButtons, [betValue, actions])

  return (

    <Form
      method="post"
      onSubmit={(event) => {
        // event.preventDefault()
        // no preventing default, becuase we want re-load data by 'empty' post request to current page
        // react-router-dom also handle this event in Router 'action' attribute
        console.log('ControlPanel : Form : onSubmit')
      }}
    >
      <Row>
        <Col md={3}>
          <input
            type="range" className="form-range"
            placeholder={betValue}
            value={betValue}
            onChange={(event)=>{
              setBetValue(event.target.value)
            }}
            min={actions.bet?.values?.min} max={actions.bet?.values?.max}
            step={actions.bet?.values?.step}
            id="betRange"
            disabled={!actions.bet.available}
          />
        </Col>
        <Col>
          <ButtonGroup className="me-2" aria-label="First group">
            {buttons}
            <Button variant='danger' type='submit' onClick={()=> {
              console.log('onClick : forceContinue')
              gameService.forceContinue(game.id)
            }}>
          force
            </Button>
          </ButtonGroup>
        </Col>
      </Row>
    </Form>
  )
}

export default ControlPanel
