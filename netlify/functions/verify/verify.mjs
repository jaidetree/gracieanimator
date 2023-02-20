import jwt from "jsonwebtoken"
import fs from "fs/promises"

export async function handler(event, context) {
	const body = JSON.parse(event.body)
	const { token } = body

	try {
		jwt.verify(token, process.env.GRACIE_STORYBOARDS_PASSWORD)
		const contents = await fs.readFile(
			"./netlify/functions/auth/storyboards.html",
			{ encoding: "utf-8" },
		)
		return {
			statusCode: 200,
			body: JSON.stringify({
				status: "ok",
				token: token,
				contents: contents,
			}),
		}
	} catch (e) {
		return {
			statusCode: 400,
			body: JSON.stringify({
				status: "fail",
				message: e.message,
			}),
		}
	}
}
