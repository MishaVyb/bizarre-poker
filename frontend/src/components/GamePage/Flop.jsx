import React from 'react'
import { Card, Row } from 'react-bootstrap'
import CardList from './CardList'
//style="border: 2px solid #07bc4c"
const Flop = ({children}) => {
  console.log(children)
  const title = (<h3 className="mb-2 text-muted">{'flop'}</h3>)
  return (
    <Row className={'d-flex justify-content-center'}>
      <Card style={{ width: '18rem', border: '2px solid'}} >
        <Card.Title className="mb-2 text-muted">game flop</Card.Title>
        <CardList>{children}</CardList>
      </Card>
    </Row>
  )
}

export default Flop