import React, { useContext, useMemo, useState } from 'react'
import { Button, ButtonGroup, Col, OverlayTrigger, Row, Tooltip  } from 'react-bootstrap'
import {Form as BootsrtrapForm }  from 'react-bootstrap'
import { Form, useLoaderData} from 'react-router-dom'
import { AuthContext, ErrorContext } from '../../context'


const ControlPanel = ({ children }) => {
  // children -- list of awaliable actions

  const actions = children
  const {game} = useLoaderData()
  const {gameService, auth} = useContext(AuthContext)
  const {setError} = useContext(ErrorContext)
  const [betValue, setBetValue] = useState(actions.bet?.values?.min)


  const getButtons = ()=>{
    let buttons = []
    for (const [name, action] of Object.entries(actions)) {
      if (name == 'kick') {
        continue
      }
      if (name == 'leave') {
        continue
      }
      if ((name == 'start' || name == 'end') && !action.available ) {
        continue
      }

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
          <OverlayTrigger key={name} placement="bottom" overlay={
            <Tooltip id={'tooltip-is-host'}>
              {action.help}
            </Tooltip>
          }
          >
            <Button type='submit' variant={variant} disabled={!action.available}
              onClick={()=> {
              // pass betValue as POST data to every actions
              // but it will take affect only on bet action,
              // other action will ignore data on server side
                gameService.post(action.url, {value: betValue}).catch((error)=> {
                  setError(error)
                })
              }}
            >
              {valueElement}{name}
            </Button>
          </OverlayTrigger>
        )
      )
    }
    return buttons
  }

  let forceShow = false
  if (!auth.user) {
    console.log('error : not user detail : [force] button will be showed just in case user is staff')
    forceShow = true
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
          <ButtonGroup>

            {buttons}
            {
              // this special action not in actions list and is allowed only for staff users
              auth.user?.is_staff || forceShow
                ? (
                  <Button variant='danger' type='submit' onClick={() => {
                    console.log('onClick : forceContinue')
                    gameService.forceContinue(game.id)
                      .catch((error)=> {
                        setError(error)
                      })
                  }}>
                    force
                  </Button>
                )
                : <></>
            }

          </ButtonGroup>
        </Col>
      </Row>
    </Form>
  )
}

export default ControlPanel
