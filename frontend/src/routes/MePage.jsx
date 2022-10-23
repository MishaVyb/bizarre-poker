import React from 'react'
import { Container, Row } from 'react-bootstrap'
import { Link, useLoaderData } from 'react-router-dom'
import Loader from '../components/UI/Loader'

const MePage = () => {
  const userDetail = useLoaderData()
  if (!userDetail) {
    return <Loader/>
  }
  return (
    <Container>
      <Row>
        <h3>Hi, {userDetail.username}!</h3>
      </Row>
      <Row>
        <Link to={'/'}><h3>go to games</h3></Link>
      </Row>
    </Container>
  )
}

export default MePage