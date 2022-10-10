import axios from "axios"
import autoBind from "auto-bind";

const urls = {
    games: '/api/v1/games/'
}

export default class GameService {
    constructor(token = null) {
      this.token = token;
      autoBind(this);
    }


    static async getAll() {
        const response = await axios.get(urls.games)
        return response.data
    }
}