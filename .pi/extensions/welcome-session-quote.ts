/**
 * NAME
 *   welcome-session-quote
 *
 * DESCRIPTION
 *   Project-local pi extension that prints a welcome message with a random
 *   quote whenever a session starts.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const CUSTOM_MESSAGE_TYPE = "welcome-session-quote";
const DISPLAY_MESSAGE = true;
const RELOAD_REASON = "reload";
const WELCOME_PREFIX = "Welcome to this pi session.";
const QUOTE_PREFIX = "Quote of the session:";

const QUOTES = [
	'"The important thing is not to stop questioning." — Albert Einstein',
	'"Somewhere, something incredible is waiting to be known." — Carl Sagan',
	'"What we know is a drop, what we don’t know is an ocean." — Isaac Newton',
	'"Science is organized knowledge. Wisdom is organized life." — Immanuel Kant',
	'"I was taught that the way of progress was neither swift nor easy." — Marie Curie',
	'"There is no great genius without some touch of madness." — Aristotle',
	'"We are all now connected by the Internet, like neurons in a giant brain." — Stephen Hawking',
	'"The best way to predict the future is to invent it." — Alan Kay',
	'"To invent, you need a good imagination and a pile of junk." — Thomas Edison',
	'"The true sign of intelligence is not knowledge but imagination." — Albert Einstein',
	'"There is nothing new to be discovered in physics now. All that remains is more and more precise measurement." — Lord Kelvin',
	'"The good thing about science is that it’s true whether or not you believe in it." — Neil deGrasse Tyson',
	'"No great mind has ever existed without a touch of madness." — Seneca',
	'"You cannot hope to build a better world without improving the individuals." — Marie Curie',
	'"Literature is the most agreeable way of ignoring life." — Fernando Pessoa',
	'"We are such stuff as dreams are made on." — William Shakespeare',
	'"The only way out is through." — Robert Frost',
	'"Not all those who wander are lost." — J. R. R. Tolkien',
	'"There is no friend as loyal as a book." — Ernest Hemingway',
	'"The future depends on what you do today." — Mahatma Gandhi',
] as const;

function pickRandomQuote(): string {
	const index = Math.floor(Math.random() * QUOTES.length);
	return QUOTES[index];
}

function buildWelcomeMessage(): string {
	return `${WELCOME_PREFIX}\n${QUOTE_PREFIX} ${pickRandomQuote()}`;
}

export default function (pi: ExtensionAPI) {
	function sendWelcomeQuote(): void {
		pi.sendMessage({
			customType: CUSTOM_MESSAGE_TYPE,
			content: buildWelcomeMessage(),
			display: DISPLAY_MESSAGE,
		});
	}

	pi.on("session_start", async (event) => {
		if (event.reason === RELOAD_REASON) {
			return;
		}

		sendWelcomeQuote();
	});

	pi.registerCommand("quote", {
		description: "Show the welcome quote on demand",
		handler: async () => {
			sendWelcomeQuote();
		},
	});
}
