import React, { useContext, useState } from 'react'
import { Alert, Button, Card, Container, Form, Row } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from '../context'
import useLoadingWrapper from '../hooks/useLoadingWrapper'
import AuthService from '../services/AuthService'

const Login = ({preventCamingBack}) => {
  // after login client goues to previous page
  // preventCamingBack option used when Login component mounts to '/logout' page
  // (we dont need go back to logout just after login)

  const defaultAuth = { username: '', password: '' }
  const [auth, setAuth] = useState(defaultAuth)
  const [errors, setErrors] = useState(null)
  const context = useContext(AuthContext)
  const navigate = useNavigate()

  const [makeLogin, isLoading] = useLoadingWrapper(async () => {
    const authService = new AuthService()
    await authService.login(auth.username, auth.password)
    setErrors(authService.error_message)

    if (!authService.error_message) {

      const userDetail = await authService.me()
      context.setAuth({
        username: auth.username,
        user: userDetail,
        token: authService.token,
      })

      localStorage.setItem('username', auth.username)
      localStorage.setItem('token', authService.token)

      if (preventCamingBack){
        navigate('/me')
      } else {
        navigate(-1)
      }
    }
  })

  const loginSubmit = async (event) => {
    event.preventDefault()
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
              {isLoading ? 'loading…' : 'login'}
            </Button>
          </Form>
        </Card>
      </Row>
    </Container>
  )
}

export default Login
