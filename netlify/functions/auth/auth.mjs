import jwt from "jsonwebtoken"
import fs from "fs/promises"

function createJWT(password) {
	return jwt.sign({ authorized: true }, password)
}

export async function handler(event, context) {
	const body = JSON.parse(event.body)

	if (body.password === process.env.GRACIE_STORYBOARDS_PASSWORD) {
		const contents = await fs.readFile(
			"./netlify/functions/auth/storyboards.html",
			{ encoding: "utf-8" },
		)
		return {
			statusCode: 200,
			body: JSON.stringify({
				status: "ok",
				token: createJWT(body.password),
				contents: contents,
			}),
		}
	}

	return {
		statusCode: 400,
		body: JSON.stringify({
			status: "fail",
			message: "Unauthorized",
		}),
	}
}
