import express from "express";
import mongodb from "mongodb";
import {readFile} from "fs/promises";

const router = express.Router();
const env = await readFile("../env.json").then(json => JSON.parse(json)).catch(() => null);

const MongoClient = mongodb.MongoClient;
const password = env.ADMIN_PASSWORD;
const url = env.PRODUCTION ? env.MONGODB_URL : env.MONGODB_URL_AWS;
const client = new MongoClient(url, {useUnifiedTopology: true});

const cookieName = "OPTIONDATA";

async function connect() {
    await client.connect();
}

await connect();

function hashCode(str) {
    let hash = 0;
    if (str.length === 0) {
        return hash;
    }
    for (let i = 0; i < str.length; i++) {
        let char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
}

router.post("/authcode", async (req, res) => {
    // generate new auth code
    try {
        const db = client.db("web");
        const authCodes = db.collection("auth_codes");

        if (password !== req.body.password) {
            return res.status(401).json({errorMsg: "Incorrect password"});
        }

        let code = 0;
        do {
            code = (Math.floor(1000 + Math.random() * 9000)).toString();
        } while (await authCodes.findOne({code}) !== null); // prevent duplicate code

        await authCodes.insertOne({code, days: req.body.days});
        setTimeout(() => {
            authCodes.deleteOne({code});
        }, 1.8e+6);
        return res.status(200).json({code});
    } catch (err) {
        console.log(err);
        console.log(req.body);
    }
});

router.post("/auth", async (req, res) => {
    // activate auth code
    try {
        const db = client.db("web");
        const authCodes = db.collection("auth_codes");
        const authIPs = db.collection("auth_ips");

        const code = await authCodes.findOne({code: {$regex: new RegExp("^" + req.body.authcode + "$", "i")}});
        if (!code) {
            return res.status(401).json({errorMsg: "Invalid auth code"});
        }

        const ip = req.headers["x-real-ip"] || req.socket.remoteAddress;
        const expirationDate = new Date();
        expirationDate.setDate(expirationDate.getDate() + code.days);
        const timestamp = expirationDate.getTime() / 1000;

        await authIPs.insertOne({ip, expiration: timestamp});
        await authCodes.deleteOne({code: {$regex: new RegExp("^" + req.body.authcode + "$", "i")}});


        return res.cookie(cookieName, hashCode(ip), {expires: expirationDate, httpOnly: true}).send();
    } catch (err) {
        console.log(err);
        console.log(req.body);
    }
});


router.post("/session", async (req, res) => {
    const ip = req.headers["x-real-ip"] || req.socket.remoteAddress;
    const db = client.db("web");
    const authIPs = db.collection("auth_ips");
    const authIP = await authIPs.findOne({ip: ip});

    // check if the ip is registered and not expired, if expired, delete the registration
    if (authIP && new Date(authIP["expiration"] * 1000).valueOf() <= new Date().valueOf()) {
        await authIPs.deleteOne({ip: ip});
    }

    // if client has cookie, authorize this client
    if (cookieName in req.cookies && req.cookies[cookieName] === hashCode(ip)) {
        return res.send();
    }

    // if client is from a registered ip, authorize this client and assign a cookie
    if (authIP) {
        return res.cookie(cookieName, hashCode(ip), {
            expires: new Date(authIP["expiration"] * 1000),
            httpOnly: true
        }).send();
    }

    return res.status(401).send();
});

export default router;

