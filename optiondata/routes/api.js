import axios from 'axios'
import {readFile} from 'fs/promises';

const env = await readFile('../env.json').then(json => JSON.parse(json)).catch(() => null);
const APIURL = env.PRODUCTION ? env.API_URL : env.API_URL_AWS
const APIKEY = env.API_KEY

global.TS = Math.floor(Date.now() / 1000)
global.FTS = Math.floor(Date.now() / 1000)

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export const getPushMessages = async () => {
    try {
        const res = await axios.post(APIURL + '/api/getnew', {
            apikey: APIKEY,
            timestamp: global.TS,
            sector: "stock",
            minprice: 1000000
        })
        const data = res.data
        if (data.timestamp != -1) {
            global.TS = data.timestamp
        }
        return data.stringify_data
    } catch (err) {
        console.log(err)
    }
}

export const getTickerString = async (ticker, options) => {
    try {
        const body = {apikey: APIKEY, ticker, limit: 10}
        for (const k in options) {
            if (options[k] != undefined && options[k] != '') body[k] = options[k];
        }
        const res = await axios.post(APIURL + '/api/gettickerstring', body)
        return res.data.stringify_data
    } catch (err) {
        console.log(err)
    }
}

export const getEtfReport = async (ticker) => {
    const res = await axios.post(APIURL + '/api/getetfreport', {
        apikey: APIKEY,
        ticker: ticker
    })
    return res.data.stringify_data
}

export const getFrequent = async () => {
    const res = await axios.post(APIURL + '/api/getfrequent', {
        apikey: APIKEY,
        timestamp: global.FTS
    })
    if (res.data.timestamp != -1) {
        global.FTS = res.data.timestamp
    }
    return res.data.stringify_data
}

export const getDailySummary = async (captain) => {
    const res = await axios.post(APIURL + '/api/getdailysummary', {
        apikey: APIKEY,
        captain: captain
    })
    return res.data.stringify_data
}

export const getBB = async () => {
    const res = await axios.post(APIURL + '/api/getbullbear', {
        apikey: APIKEY
    })
    return res.data.stringify_data
}

export const getInsiderNews = async (t) => {
    const res = await axios.post(APIURL + '/api/getinsidernews', {
        apikey: APIKEY,
        ticker: t
    })
    return res.data.stringify_data
}

export const getTradingAnalysis = async (t, i) => {
    const res = await axios.post(APIURL + '/api/gettickerchart', {
        apikey: APIKEY,
        ticker: t,
        interval: i
    })
    return res.data.chart
}

export const getArkMove = async () => {
    const res = await axios.post(APIURL + '/api/getarktrades', {
        apikey: APIKEY
    })
    return res.data.stringify_data
}

export const getArkHoldings = async (t) => {
    const res = await axios.post(APIURL + '/api/getarkholdings', {
        apikey: APIKEY,
        ticker: t
    })
    return res.data.stringify_data
}