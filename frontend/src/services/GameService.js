import axios from 'axios'
import autoBind from 'auto-bind'
import delay from '../utils/functools'

const ENDPOINTS = {
  games: '/api/v1/games/',
  gameDetail: '/api/v1/games/{game_pk}/',

  players: '/api/v1/games/{game_pk}/players/',
  playersDetail: '/api/v1/games/{game_pk}/players/{username}/',
  playersMe: '/api/v1/games/{game_pk}/players/me/',
  playersOther: '/api/v1/games/{game_pk}/players/other/',

  playersPreforms: '/api/v1/games/{game_pk}/playersPreforms/',

  actions: '/api/v1/games/{game_pk}/actions/',
  forceContinue: '/api/v1/games/{game_pk}/actions/forceContinue/',
}

export default class GameService {
  constructor(token = null) {
    this.token = token
    autoBind(this)
  }

  get config() {
    return {
      headers: {
        Authorization: `Token ${this.token}`,
      },
    }
  }

  ///////////////////////////// get game ///////////////////////////////////////

  async getAll() {
    const response = await axios.get(ENDPOINTS.games)
    return response.data
  }
  async getCreateChoices() {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    await delay(500)
    const response = await axios.options(ENDPOINTS.games, this.config)
    return response.data?.actions?.POST?.config_name?.choices
  }

  ////////////////////////////// get player ////////////////////////////////////////

  async getPlayed() {}

  async getOther() {}

  async getHosted() {}

  ////////////////////////////// create destroy game  ////////////////////////////////////////

  async create(config_name) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const response = await axios.post(ENDPOINTS.games, {config_name}, this.config)
    return response.data
  }

  ////////////////////////////// create destroy players  ////////////////////////////////////////

  async join(gameId) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const response = await axios.post(
      ENDPOINTS.playersPreforms.replace('{game_pk}', gameId), {}, this.config
    )
    return response.data
  }

  async approveJoin(gameId, username) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const response = await axios.post(
      ENDPOINTS.players.replace('{game_pk}', gameId), {user: username}, this.config
    )
    return response.data
  }

  async kick(gameId, username) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const url = ENDPOINTS.playersDetail.replace('{game_pk}', gameId).replace('{username}', username)
    const response = await axios.delete(url, this.config)
    return response.data
  }

  async leave(gameId, username) {
    // just a riderection to the same post request
    return this.kick(gameId, username)
  }


  ////////////////////////////// update  ////////////////////////////////////////

  async post(url, data = {}) {
    // for acting special actions with POST request
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const response = await axios.post(url, data, this.config)
    return response.data
  }

  // tmp solution
  // this action should be provided by server with among other game actions with changing its stage
  async forceContinue(gameId, data = {}) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }
    const response = await axios.post(
      ENDPOINTS.forceContinue.replace('{game_pk}', gameId),
      data,
      this.config
    )
    return response.data

  }





  ////////////////////////////// LOADERS  ////////////////////////////////////////

  async gamesPageLoader() {
    // seperated full loader includes a few requsts
    if (!this.auth) {
      return await this.getAll()
    }

    const played = await this.getPlayed()
    const other = await this.getOther()
    return { played, other }
  }




  async gameDetailLoader({ params }) {
    // seperated full loader includes a few requsts
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    console.log('info : gameDetailLoader')
    let response = await axios.get(
      ENDPOINTS.gameDetail.replace('{game_pk}', params.gameId),
      this.config
    )
    const game = response.data

    response = await axios.get(
      ENDPOINTS.players.replace('{game_pk}', params.gameId),
      this.config
    )
    const playersAll = response.data

    response = await axios.get(
      ENDPOINTS.playersMe.replace('{game_pk}', params.gameId),
      this.config
    )
    const playerMe = response.data

    response = await axios.get(
      ENDPOINTS.playersOther.replace('{game_pk}', params.gameId),
      this.config
    )
    const playersOther = response.data

    response = await axios.get(
      ENDPOINTS.actions.replace('{game_pk}', params.gameId),
      this.config
    )
    const actions = response.data

    return { game, playersAll, playerMe, playersOther, actions }
  }
}
