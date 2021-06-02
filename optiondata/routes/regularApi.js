import express from "express";
import queue from "express-queue";
import {getTickerString, getTradingAnalysis} from "./api.js";

const router = express.Router();
const taQueue = [];
let sendingTA = false;

router.post("/realtime", async (req, res) => {
    const options = req.body;
    const everything = await getTickerString("ALL", options);
    if (!everything) {
        return;
    }
    const s = everything.split("\n\n");

    return res.send(s.slice(0, s.length - 1));
});

router.post("/ticker", async (req, res) => {
    const {ticker} = req.body;
    const options = req.body;
    options.page = 0;
    const result = await getTickerString(ticker, options);
    if (!result) {
        return;
    }
    const s = result.split("\n\n");
    return res.send(s.slice(0, s.length - 1));
});

router.post("/ta", async (req, res) => {
    taQueue.push([req.body.ticker, req.body.interval, res]);
});

setInterval(async () => {
    if (taQueue.length == 0 || sendingTA) return;
    sendingTA = true;
    const taPair = taQueue.shift();
    const result = await getTradingAnalysis(taPair[0], taPair[1]);
    if (Number.isInteger(result)) {
        taPair[2].status(400).send({message: result});
    }
    taPair[2].send(result);
    sendingTA = false;
}, 10000);

export default router;
