import React from 'react'
import { Badge, Col, Container, Row} from 'react-bootstrap'
import Navbar from 'react-bootstrap/Navbar'
import { Link } from 'react-router-dom'
import { useContext } from 'react'
import { AuthContext } from '../../context'

const MyNavbar = () => {
  const { auth, setAuth } = useContext(AuthContext)

  let links = []
  if (auth) {
    links[0] = (<Link to={'logout'} key={'logout'}>logout</Link>)

  } else {
    links[0] = (<Link to={'login'} key={'login'}><Badge>login</Badge></Link>)
    links[1] = (<Link to={'signup'} key={'signup'}>signup</Link>)
  }

  return (
    <Navbar>
      <Container>
        <Navbar.Brand>
          <Link to={'/'}>bizarre poker</Link>
        </Navbar.Brand>
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            <Link to={'/me'}>
              <Badge>{auth?.username}</Badge>
            </Link>
            {links}
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default MyNavbar
