import React, { useContext, useState } from 'react'
import { Alert, Button, Card, Container, Form, Row } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from '../context'
import useLoadingWrapper from '../hooks/useLoadingWrapper'
import AuthService from '../services/AuthService'


const SignUp = () => {
  const defaultAuth = { username: '', password: '' }
  const [auth, setAuth] = useState(defaultAuth)
  const [errors, setErrors] = useState(null)
  const context = useContext(AuthContext)
  const navigate = useNavigate()

  const [makeLogin, isLoading] = useLoadingWrapper(async () => {
    const authService = new AuthService()
    await authService.signUp(auth.username, auth.password)
    setErrors(authService.error_message)

    if (!authService.error_message) {
      console.log('sign up and login -> got token: ' + authService.token)
      context.setAuth({
        username: auth.username,
        token: authService.token,
      })
      localStorage.setItem('username', auth.username)
      localStorage.setItem('token', authService.token)
      navigate(-1)
    }
  })

  const loginSubmit = async (event) => {
    event.preventDefault()
    console.log('logging in with:')
    console.log(auth)
    makeLogin()
  }

  let errorItems
  if (errors) {
    errorItems = Object.entries(errors).map(([key, value]) => (
      <Alert variant="danger" key={key}>
        <h5>{key}</h5>
        {value}
      </Alert>
    ))
  }

  return (
    <Container  >
      <Row className="justify-content-center">
        <Card style={{ width: '18rem' }}>
          <Form onSubmit={loginSubmit}>
            <Form.Group>
              <Form.Control
                type="login"
                placeholder="username"
                value={auth.username}
                onChange={(event) =>
                  setAuth({ ...auth, username: event.target.value })
                }
              />
            </Form.Group>
            <Form.Group>
              <Form.Control
                type="password"
                placeholder="password"
                value={auth.password}
                onChange={(event) =>
                  setAuth({ ...auth, password: event.target.value })
                }
              />
            </Form.Group>
            {errorItems}
            <Button variant="primary" type="submit" disabled={isLoading}>
              {isLoading ? 'loading…' : 'sign up'}
            </Button>
          </Form>
        </Card>
      </Row>
    </Container>
  )
}
export default SignUp