import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import cookieParser from "cookie-parser";

const app = express();
app.use(cors({origin: true, credentials: true}));

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: false}));
app.use(cookieParser());

const PORT = 5001;
app.listen(PORT, () => {
    console.log(`listening on port ${PORT}`);
});


import regularApiRoutes from "./regularApi.js";

app.use("/api", regularApiRoutes);

import adminApiRoutes from "./adminApi.js";

app.use("/api/admin", adminApiRoutes);