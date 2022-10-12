import React from 'react'

import { Badge, Card, Col, Container, Row } from 'react-bootstrap'

const CardList = ({title, children}) => {
  if (!children || !children[0]){
    return <></>
  }

  return (
    <Row className='d-flex justify-content-center'>
      <Col md="auto"><h5>{title}</h5></Col>
      <Col md="auto"><Badge bg="success">{children}</Badge></Col>
    </Row>
  )
}

export default CardList