/**
 * NAME
 *   pi-environment-augmentations
 *
 * SYNOPSIS
 *   /augmentations
 *
 * DESCRIPTION
 *   Project-local pi extension that inventories pi environment augmentations on
 *   demand. The report includes discovered local customization files,
 *   configured package sources, and currently available extension/prompt/skill
 *   commands in the active session.
 */

import { access, readFile, readdir } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, join, relative, resolve } from "node:path";
import type { ExtensionAPI, SlashCommandInfo } from "@mariozechner/pi-coding-agent";

const ZERO = 0;
const ONE = 1;
const TWO = 2;

const COMMAND_NAME = "augmentations";
const COMMAND_DESCRIPTION = "Show your pi environment augmentations";
const CUSTOM_MESSAGE_TYPE = "pi-environment-augmentations";
const DISPLAY_MESSAGE = true;

const HOME_PREFIX = "~";
const CURRENT_DIRECTORY_TOKEN = ".";
const DOT_PI = ".pi";
const AGENT_DIRECTORY = "agent";
const EXTENSIONS_DIRECTORY = "extensions";
const SKILLS_DIRECTORY = "skills";
const PROMPTS_DIRECTORY = "prompts";
const THEMES_DIRECTORY = "themes";
const SETTINGS_FILE_NAME = "settings.json";
const KEYBINDINGS_FILE_NAME = "keybindings.json";
const SYSTEM_PROMPT_FILE_NAME = "SYSTEM.md";
const APPEND_SYSTEM_PROMPT_FILE_NAME = "APPEND_SYSTEM.md";
const SKILL_FILE_NAME = "SKILL.md";

const SETTINGS_KEY_PACKAGES = "packages";
const SETTINGS_KEY_EXTENSIONS = "extensions";
const SETTINGS_KEY_SKILLS = "skills";
const SETTINGS_KEY_PROMPTS = "prompts";
const SETTINGS_KEY_THEMES = "themes";
const SETTINGS_KEY_DEFAULT_PROVIDER = "defaultProvider";
const SETTINGS_KEY_DEFAULT_MODEL = "defaultModel";
const SETTINGS_KEY_DEFAULT_THINKING_LEVEL = "defaultThinkingLevel";
const SETTINGS_KEY_THEME = "theme";

const SOURCE_EXTENSION = "extension";
const SOURCE_PROMPT = "prompt";
const SOURCE_SKILL = "skill";

const SECTION_SEPARATOR = "\n\n";
const LINE_PREFIX = "- ";
const INDENT = "  ";
const NONE_LINE = "- none";
const UNKNOWN_LINE = "- unknown";
const STATUS_PRESENT = "present";
const STATUS_MISSING = "missing";
const STATUS_INVALID = "invalid JSON";

const TITLE = "# Pi Environment Augmentations";
const SUMMARY_HEADING = "## Summary";
const FILES_HEADING = "## Customization Files";
const PACKAGE_HEADING = "## Configured Package Sources";
const COMMANDS_HEADING = "## Active Augmentation Commands";
const SETTINGS_HEADING = "## Effective Settings Hints";

const GLOBAL_SCOPE_LABEL = "global";
const PROJECT_SCOPE_LABEL = "project";
const EXTENSION_LABEL = "extensions";
const SKILL_LABEL = "skills";
const PROMPT_LABEL = "prompts";
const THEME_LABEL = "themes";
const SETTINGS_LABEL = "settings";
const KEYBINDINGS_LABEL = "keybindings";
const SYSTEM_PROMPT_LABEL = "system prompts";
const PACKAGE_LABEL = "packages";
const COMMAND_LABEL = "commands";

const GLOBAL_SETTINGS_LABEL = "Global settings";
const PROJECT_SETTINGS_LABEL = "Project settings";
const GLOBAL_KEYBINDINGS_LABEL = "Global keybindings";
const PROJECT_KEYBINDINGS_LABEL = "Project keybindings";
const GLOBAL_SYSTEM_LABEL = "Global SYSTEM.md";
const PROJECT_SYSTEM_LABEL = "Project SYSTEM.md";
const GLOBAL_APPEND_SYSTEM_LABEL = "Global APPEND_SYSTEM.md";
const PROJECT_APPEND_SYSTEM_LABEL = "Project APPEND_SYSTEM.md";
const GLOBAL_EXTENSIONS_LABEL = "Global extensions";
const PROJECT_EXTENSIONS_LABEL = "Project extensions";
const GLOBAL_SKILLS_LABEL = "Global skills";
const PROJECT_SKILLS_LABEL = "Project skills";
const GLOBAL_PROMPTS_LABEL = "Global prompts";
const PROJECT_PROMPTS_LABEL = "Project prompts";
const GLOBAL_THEMES_LABEL = "Global themes";
const PROJECT_THEMES_LABEL = "Project themes";
const GLOBAL_SETTINGS_CONFIG_LABEL = "Global configured resource paths";
const PROJECT_SETTINGS_CONFIG_LABEL = "Project configured resource paths";

const FILE_LABEL_SEPARATOR = ": ";
const STATUS_SEPARATOR = " — ";
const PATHS_LABEL = "paths";
const FILES_LABEL = "files";
const RAW_VALUES_LABEL = "raw entries";
const PROVIDER_LABEL = "defaultProvider";
const MODEL_LABEL = "defaultModel";
const THINKING_LABEL = "defaultThinkingLevel";
const THEME_SETTING_LABEL = "theme";

const EXTENSION_COMMANDS_LABEL = "Extension commands";
const PROMPT_COMMANDS_LABEL = "Prompt commands";
const SKILL_COMMANDS_LABEL = "Skill commands";
const DESCRIPTION_SEPARATOR = " — ";
const PATH_SEPARATOR = " @ ";

const RESOURCE_SETTING_KEYS = [
	SETTINGS_KEY_PACKAGES,
	SETTINGS_KEY_EXTENSIONS,
	SETTINGS_KEY_SKILLS,
	SETTINGS_KEY_PROMPTS,
	SETTINGS_KEY_THEMES,
] as const;

const SETTING_HINT_KEYS = [
	SETTINGS_KEY_DEFAULT_PROVIDER,
	SETTINGS_KEY_DEFAULT_MODEL,
	SETTINGS_KEY_DEFAULT_THINKING_LEVEL,
	SETTINGS_KEY_THEME,
] as const;

type JsonRecord = Record<string, unknown>;

type FilePresence = {
	label: string;
	path: string;
	present: boolean;
};

type SettingsSummary = {
	label: string;
	path: string;
	present: boolean;
	valid: boolean;
	data: JsonRecord;
};

type InventorySection = {
	label: string;
	files: string[];
};

type CommandGroup = {
	label: string;
	source: typeof SOURCE_EXTENSION | typeof SOURCE_PROMPT | typeof SOURCE_SKILL;
};

/**
 * NAME
 *   pathExists
 *
 * DESCRIPTION
 *   Returns whether a file-system path is accessible. Errors are treated as a
 *   negative result so the report remains best-effort.
 */
async function pathExists(path: string): Promise<boolean> {
	try {
		await access(path);
		return true;
	} catch {
		return false;
	}
}

/**
 * NAME
 *   readSettingsSummary
 *
 * DESCRIPTION
 *   Reads a pi settings file and returns a parsed summary. Invalid JSON is
 *   reported without throwing so the command can still show the rest of the
 *   environment.
 */
async function readSettingsSummary(label: string, path: string): Promise<SettingsSummary> {
	if (!(await pathExists(path))) {
		return { label, path, present: false, valid: false, data: {} };
	}

	try {
		const content = await readFile(path, "utf8");
		const parsed = JSON.parse(content) as unknown;
		const data = isJsonRecord(parsed) ? parsed : {};
		return { label, path, present: true, valid: true, data };
	} catch {
		return { label, path, present: true, valid: false, data: {} };
	}
}

/**
 * NAME
 *   isJsonRecord
 *
 * DESCRIPTION
 *   Narrows unknown JSON values to a plain object map.
 */
function isJsonRecord(value: unknown): value is JsonRecord {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * NAME
 *   collectFilesRecursive
 *
 * DESCRIPTION
 *   Recursively collects files under a directory. The optional predicate keeps
 *   the traversal generic for extensions, prompts, themes, and skill markers.
 */
async function collectFilesRecursive(
	rootPath: string,
	predicate?: (filePath: string) => boolean,
): Promise<string[]> {
	if (!(await pathExists(rootPath))) {
		return [];
	}

	const entries = await readdir(rootPath, { withFileTypes: true });
	const files: string[] = [];

	for (const entry of entries) {
		const entryPath = join(rootPath, entry.name);
		if (entry.isDirectory()) {
			files.push(...(await collectFilesRecursive(entryPath, predicate)));
			continue;
		}

		if (!entry.isFile()) {
			continue;
		}

		if (!predicate || predicate(entryPath)) {
			files.push(entryPath);
		}
	}

	return files.sort();
}

/**
 * NAME
 *   hasExtension
 *
 * DESCRIPTION
 *   Reports whether a file path ends with one of the allowed suffixes.
 */
function hasExtension(filePath: string, suffixes: readonly string[]): boolean {
	return suffixes.some((suffix) => filePath.endsWith(suffix));
}

/**
 * NAME
 *   formatPathForReport
 *
 * DESCRIPTION
 *   Formats paths relative to the current project when possible and shortens
 *   home-directory paths with a leading tilde for readability.
 */
function formatPathForReport(path: string, cwd: string, homePath: string): string {
	const resolvedPath = resolve(path);
	const resolvedCwd = resolve(cwd);
	const resolvedHome = resolve(homePath);

	if (resolvedPath === resolvedCwd) {
		return CURRENT_DIRECTORY_TOKEN;
	}

	if (resolvedPath.startsWith(`${resolvedCwd}/`) || resolvedPath.startsWith(`${resolvedCwd}\\`)) {
		return relative(resolvedCwd, resolvedPath);
	}

	if (resolvedPath === resolvedHome) {
		return HOME_PREFIX;
	}

	if (resolvedPath.startsWith(`${resolvedHome}/`) || resolvedPath.startsWith(`${resolvedHome}\\`)) {
		return `${HOME_PREFIX}/${relative(resolvedHome, resolvedPath).replace(/\\/g, "/")}`;
	}

	return resolvedPath;
}

/**
 * NAME
 *   toConfiguredPathList
 *
 * DESCRIPTION
 *   Normalizes a resource setting value to a printable string array. Package
 *   entries may be strings or filter objects; objects are serialized compactly.
 */
function toConfiguredPathList(value: unknown): string[] {
	if (!Array.isArray(value)) {
		return [];
	}

	return value.map((entry) => {
		if (typeof entry === "string") {
			return entry;
		}

		return JSON.stringify(entry);
	});
}

/**
 * NAME
 *   buildFilePresenceLines
 *
 * DESCRIPTION
 *   Renders file-presence summaries for key customization files.
 */
function buildFilePresenceLines(items: readonly FilePresence[], cwd: string, homePath: string): string[] {
	return items.map((item) => {
		const status = item.present ? STATUS_PRESENT : STATUS_MISSING;
		return `${LINE_PREFIX}${item.label}${FILE_LABEL_SEPARATOR}${formatPathForReport(item.path, cwd, homePath)}${STATUS_SEPARATOR}${status}`;
	});
}

/**
 * NAME
 *   buildSettingsLines
 *
 * DESCRIPTION
 *   Renders compact setting hints for provider/model/thinking/theme so the
 *   operator can see important environment overrides at a glance.
 */
function buildSettingsLines(items: readonly SettingsSummary[], cwd: string, homePath: string): string[] {
	const lines: string[] = [];

	for (const item of items) {
		if (!item.present) {
			lines.push(
				`${LINE_PREFIX}${item.label}${FILE_LABEL_SEPARATOR}${formatPathForReport(item.path, cwd, homePath)}${STATUS_SEPARATOR}${STATUS_MISSING}`,
			);
			continue;
		}

		if (!item.valid) {
			lines.push(
				`${LINE_PREFIX}${item.label}${FILE_LABEL_SEPARATOR}${formatPathForReport(item.path, cwd, homePath)}${STATUS_SEPARATOR}${STATUS_INVALID}`,
			);
			continue;
		}

		lines.push(
			`${LINE_PREFIX}${item.label}${FILE_LABEL_SEPARATOR}${formatPathForReport(item.path, cwd, homePath)}${STATUS_SEPARATOR}${STATUS_PRESENT}`,
		);

		for (const key of SETTING_HINT_KEYS) {
			const value = item.data[key];
			if (typeof value === "string") {
				lines.push(`${INDENT}${LINE_PREFIX}${key}${FILE_LABEL_SEPARATOR}${value}`);
			}
		}
	}

	return lines;
}

/**
 * NAME
 *   buildInventorySectionLines
 *
 * DESCRIPTION
 *   Renders resource inventory sections with either file lists or an explicit
 *   none marker.
 */
function buildInventorySectionLines(items: readonly InventorySection[]): string[] {
	const lines: string[] = [];

	for (const item of items) {
		lines.push(`${LINE_PREFIX}${item.label}`);
		if (item.files.length === ZERO) {
			lines.push(`${INDENT}${NONE_LINE}`);
			continue;
		}

		for (const file of item.files) {
			lines.push(`${INDENT}${LINE_PREFIX}${file}`);
		}
	}

	return lines;
}

/**
 * NAME
 *   buildCommandLines
 *
 * DESCRIPTION
 *   Groups the currently available slash commands by source so the report shows
 *   which augmentation commands are active in the present session.
 */
function buildCommandLines(commands: readonly SlashCommandInfo[]): string[] {
	const groups: readonly CommandGroup[] = [
		{ label: EXTENSION_COMMANDS_LABEL, source: SOURCE_EXTENSION },
		{ label: PROMPT_COMMANDS_LABEL, source: SOURCE_PROMPT },
		{ label: SKILL_COMMANDS_LABEL, source: SOURCE_SKILL },
	];
	const lines: string[] = [];

	for (const group of groups) {
		lines.push(`${LINE_PREFIX}${group.label}`);
		const groupCommands = commands.filter((command) => command.source === group.source);
		if (groupCommands.length === ZERO) {
			lines.push(`${INDENT}${NONE_LINE}`);
			continue;
		}

		for (const command of groupCommands) {
			const description = command.description ? `${DESCRIPTION_SEPARATOR}${command.description}` : "";
			const path = command.sourceInfo.path ? `${PATH_SEPARATOR}${command.sourceInfo.path}` : "";
			lines.push(`${INDENT}${LINE_PREFIX}/${command.name}${description}${path}`);
		}
	}

	return lines;
}

/**
 * NAME
 *   makeSection
 *
 * DESCRIPTION
 *   Builds a markdown section while keeping empty sections explicit.
 */
function makeSection(title: string, lines: readonly string[]): string {
	const body = lines.length > ZERO ? lines.join("\n") : NONE_LINE;
	return `${title}\n${body}`;
}

/**
 * NAME
 *   buildSummaryLines
 *
 * DESCRIPTION
 *   Produces a compact count summary from the collected inventory.
 */
function buildSummaryLines(sections: readonly InventorySection[], packageCount: number, commandCount: number): string[] {
	const totalFiles = sections.reduce((sum, section) => sum + section.files.length, ZERO);
	return [
		`${LINE_PREFIX}${SETTINGS_LABEL}${FILE_LABEL_SEPARATOR}${sections[ZERO]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${KEYBINDINGS_LABEL}${FILE_LABEL_SEPARATOR}${sections[ONE]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${SYSTEM_PROMPT_LABEL}${FILE_LABEL_SEPARATOR}${sections[TWO]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${EXTENSION_LABEL}${FILE_LABEL_SEPARATOR}${sections[3]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${SKILL_LABEL}${FILE_LABEL_SEPARATOR}${sections[4]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${PROMPT_LABEL}${FILE_LABEL_SEPARATOR}${sections[5]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${THEME_LABEL}${FILE_LABEL_SEPARATOR}${sections[6]?.files.length ?? ZERO}`,
		`${LINE_PREFIX}${PACKAGE_LABEL}${FILE_LABEL_SEPARATOR}${packageCount}`,
		`${LINE_PREFIX}${COMMAND_LABEL}${FILE_LABEL_SEPARATOR}${commandCount}`,
		`${LINE_PREFIX}${FILES_LABEL}${FILE_LABEL_SEPARATOR}${totalFiles}`,
	];
}

export default function environmentAugmentationsExtension(pi: ExtensionAPI) {
	pi.registerCommand(COMMAND_NAME, {
		description: COMMAND_DESCRIPTION,
		handler: async (_args, ctx) => {
			const homePath = homedir();
			const globalPiRoot = join(homePath, DOT_PI, AGENT_DIRECTORY);
			const projectPiRoot = resolve(ctx.cwd, DOT_PI);

			const globalSettingsPath = join(globalPiRoot, SETTINGS_FILE_NAME);
			const projectSettingsPath = join(projectPiRoot, SETTINGS_FILE_NAME);
			const globalKeybindingsPath = join(globalPiRoot, KEYBINDINGS_FILE_NAME);
			const projectKeybindingsPath = join(projectPiRoot, KEYBINDINGS_FILE_NAME);
			const globalSystemPath = join(globalPiRoot, SYSTEM_PROMPT_FILE_NAME);
			const projectSystemPath = join(projectPiRoot, SYSTEM_PROMPT_FILE_NAME);
			const globalAppendSystemPath = join(globalPiRoot, APPEND_SYSTEM_PROMPT_FILE_NAME);
			const projectAppendSystemPath = join(projectPiRoot, APPEND_SYSTEM_PROMPT_FILE_NAME);
			const globalExtensionsPath = join(globalPiRoot, EXTENSIONS_DIRECTORY);
			const projectExtensionsPath = join(projectPiRoot, EXTENSIONS_DIRECTORY);
			const globalSkillsPath = join(globalPiRoot, SKILLS_DIRECTORY);
			const projectSkillsPath = join(projectPiRoot, SKILLS_DIRECTORY);
			const globalPromptsPath = join(globalPiRoot, PROMPTS_DIRECTORY);
			const projectPromptsPath = join(projectPiRoot, PROMPTS_DIRECTORY);
			const globalThemesPath = join(globalPiRoot, THEMES_DIRECTORY);
			const projectThemesPath = join(projectPiRoot, THEMES_DIRECTORY);

			const globalSettings = await readSettingsSummary(GLOBAL_SETTINGS_LABEL, globalSettingsPath);
			const projectSettings = await readSettingsSummary(PROJECT_SETTINGS_LABEL, projectSettingsPath);

			const settingsPresence: FilePresence[] = [
				{ label: GLOBAL_SETTINGS_LABEL, path: globalSettingsPath, present: globalSettings.present },
				{ label: PROJECT_SETTINGS_LABEL, path: projectSettingsPath, present: projectSettings.present },
			];

			const keybindingPresence: FilePresence[] = [
				{ label: GLOBAL_KEYBINDINGS_LABEL, path: globalKeybindingsPath, present: await pathExists(globalKeybindingsPath) },
				{ label: PROJECT_KEYBINDINGS_LABEL, path: projectKeybindingsPath, present: await pathExists(projectKeybindingsPath) },
			];

			const systemPresence: FilePresence[] = [
				{ label: GLOBAL_SYSTEM_LABEL, path: globalSystemPath, present: await pathExists(globalSystemPath) },
				{ label: PROJECT_SYSTEM_LABEL, path: projectSystemPath, present: await pathExists(projectSystemPath) },
				{ label: GLOBAL_APPEND_SYSTEM_LABEL, path: globalAppendSystemPath, present: await pathExists(globalAppendSystemPath) },
				{ label: PROJECT_APPEND_SYSTEM_LABEL, path: projectAppendSystemPath, present: await pathExists(projectAppendSystemPath) },
			];

			const extensionFiles = [
				...(await collectFilesRecursive(globalExtensionsPath, (filePath) => hasExtension(filePath, [".ts", ".js"]))),
				...(await collectFilesRecursive(projectExtensionsPath, (filePath) => hasExtension(filePath, [".ts", ".js"]))),
			].map((filePath) => formatPathForReport(filePath, ctx.cwd, homePath));

			const skillFiles = [
				...(await collectFilesRecursive(globalSkillsPath, (filePath) => filePath.endsWith(SKILL_FILE_NAME) || filePath.endsWith(".md"))),
				...(await collectFilesRecursive(projectSkillsPath, (filePath) => filePath.endsWith(SKILL_FILE_NAME) || filePath.endsWith(".md"))),
			].map((filePath) => formatPathForReport(filePath, ctx.cwd, homePath));

			const promptFiles = [
				...(await collectFilesRecursive(globalPromptsPath, (filePath) => filePath.endsWith(".md"))),
				...(await collectFilesRecursive(projectPromptsPath, (filePath) => filePath.endsWith(".md"))),
			].map((filePath) => formatPathForReport(filePath, ctx.cwd, homePath));

			const themeFiles = [
				...(await collectFilesRecursive(globalThemesPath, (filePath) => filePath.endsWith(".json"))),
				...(await collectFilesRecursive(projectThemesPath, (filePath) => filePath.endsWith(".json"))),
			].map((filePath) => formatPathForReport(filePath, ctx.cwd, homePath));

			const configuredPackageEntries = [
				...toConfiguredPathList(globalSettings.data[SETTINGS_KEY_PACKAGES]),
				...toConfiguredPathList(projectSettings.data[SETTINGS_KEY_PACKAGES]),
			];

			const configuredExtensionEntries = [
				...toConfiguredPathList(globalSettings.data[SETTINGS_KEY_EXTENSIONS]),
				...toConfiguredPathList(projectSettings.data[SETTINGS_KEY_EXTENSIONS]),
			];

			const configuredSkillEntries = [
				...toConfiguredPathList(globalSettings.data[SETTINGS_KEY_SKILLS]),
				...toConfiguredPathList(projectSettings.data[SETTINGS_KEY_SKILLS]),
			];

			const configuredPromptEntries = [
				...toConfiguredPathList(globalSettings.data[SETTINGS_KEY_PROMPTS]),
				...toConfiguredPathList(projectSettings.data[SETTINGS_KEY_PROMPTS]),
			];

			const configuredThemeEntries = [
				...toConfiguredPathList(globalSettings.data[SETTINGS_KEY_THEMES]),
				...toConfiguredPathList(projectSettings.data[SETTINGS_KEY_THEMES]),
			];

			const inventorySections: InventorySection[] = [
				{
					label: SETTINGS_LABEL,
					files: settingsPresence.filter((item) => item.present).map((item) => formatPathForReport(item.path, ctx.cwd, homePath)),
				},
				{
					label: KEYBINDINGS_LABEL,
					files: keybindingPresence.filter((item) => item.present).map((item) => formatPathForReport(item.path, ctx.cwd, homePath)),
				},
				{
					label: SYSTEM_PROMPT_LABEL,
					files: systemPresence.filter((item) => item.present).map((item) => formatPathForReport(item.path, ctx.cwd, homePath)),
				},
				{ label: EXTENSION_LABEL, files: extensionFiles },
				{ label: SKILL_LABEL, files: skillFiles },
				{ label: PROMPT_LABEL, files: promptFiles },
				{ label: THEME_LABEL, files: themeFiles },
			];

			const fileLines = [
				...buildFilePresenceLines(settingsPresence, ctx.cwd, homePath),
				...buildFilePresenceLines(keybindingPresence, ctx.cwd, homePath),
				...buildFilePresenceLines(systemPresence, ctx.cwd, homePath),
				...buildInventorySectionLines([
					{
						label: GLOBAL_EXTENSIONS_LABEL,
						files: (await collectFilesRecursive(globalExtensionsPath, (filePath) => hasExtension(filePath, [".ts", ".js"]))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: PROJECT_EXTENSIONS_LABEL,
						files: (await collectFilesRecursive(projectExtensionsPath, (filePath) => hasExtension(filePath, [".ts", ".js"]))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: GLOBAL_SKILLS_LABEL,
						files: (await collectFilesRecursive(globalSkillsPath, (filePath) => filePath.endsWith(SKILL_FILE_NAME) || filePath.endsWith(".md"))).map(
							(filePath) => formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: PROJECT_SKILLS_LABEL,
						files: (await collectFilesRecursive(projectSkillsPath, (filePath) => filePath.endsWith(SKILL_FILE_NAME) || filePath.endsWith(".md"))).map(
							(filePath) => formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: GLOBAL_PROMPTS_LABEL,
						files: (await collectFilesRecursive(globalPromptsPath, (filePath) => filePath.endsWith(".md"))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: PROJECT_PROMPTS_LABEL,
						files: (await collectFilesRecursive(projectPromptsPath, (filePath) => filePath.endsWith(".md"))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: GLOBAL_THEMES_LABEL,
						files: (await collectFilesRecursive(globalThemesPath, (filePath) => filePath.endsWith(".json"))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
					{
						label: PROJECT_THEMES_LABEL,
						files: (await collectFilesRecursive(projectThemesPath, (filePath) => filePath.endsWith(".json"))).map((filePath) =>
							formatPathForReport(filePath, ctx.cwd, homePath),
						),
					},
				]),
			];

			const packageLines = [
				`${LINE_PREFIX}${GLOBAL_SETTINGS_CONFIG_LABEL}`,
				...(toConfiguredPathList(globalSettings.data[SETTINGS_KEY_PACKAGES]).length > ZERO
					? toConfiguredPathList(globalSettings.data[SETTINGS_KEY_PACKAGES]).map((entry) => `${INDENT}${LINE_PREFIX}${entry}`)
					: [`${INDENT}${NONE_LINE}`]),
				`${LINE_PREFIX}${PROJECT_SETTINGS_CONFIG_LABEL}`,
				...(toConfiguredPathList(projectSettings.data[SETTINGS_KEY_PACKAGES]).length > ZERO
					? toConfiguredPathList(projectSettings.data[SETTINGS_KEY_PACKAGES]).map((entry) => `${INDENT}${LINE_PREFIX}${entry}`)
					: [`${INDENT}${NONE_LINE}`]),
			];

			const resourceConfigLines = [
				`${LINE_PREFIX}${GLOBAL_SETTINGS_CONFIG_LABEL}${FILE_LABEL_SEPARATOR}${PATHS_LABEL}`,
				...(configuredExtensionEntries.length > ZERO ? configuredExtensionEntries.map((entry) => `${INDENT}${LINE_PREFIX}${entry}`) : [`${INDENT}${NONE_LINE}`]),
				`${LINE_PREFIX}${PROJECT_SETTINGS_CONFIG_LABEL}${FILE_LABEL_SEPARATOR}${RAW_VALUES_LABEL}`,
				...(configuredSkillEntries.length + configuredPromptEntries.length + configuredThemeEntries.length > ZERO
					? [
						...configuredSkillEntries.map((entry) => `${INDENT}${LINE_PREFIX}${SETTINGS_KEY_SKILLS}${FILE_LABEL_SEPARATOR}${entry}`),
						...configuredPromptEntries.map((entry) => `${INDENT}${LINE_PREFIX}${SETTINGS_KEY_PROMPTS}${FILE_LABEL_SEPARATOR}${entry}`),
						...configuredThemeEntries.map((entry) => `${INDENT}${LINE_PREFIX}${SETTINGS_KEY_THEMES}${FILE_LABEL_SEPARATOR}${entry}`),
					]
					: [`${INDENT}${NONE_LINE}`]),
			];

			const commands = pi.getCommands().filter(
				(command) => command.source === SOURCE_EXTENSION || command.source === SOURCE_PROMPT || command.source === SOURCE_SKILL,
			);

			const report = [
				TITLE,
				makeSection(SUMMARY_HEADING, buildSummaryLines(inventorySections, configuredPackageEntries.length, commands.length)),
				makeSection(SETTINGS_HEADING, buildSettingsLines([globalSettings, projectSettings], ctx.cwd, homePath)),
				makeSection(FILES_HEADING, [...fileLines, ...resourceConfigLines]),
				makeSection(PACKAGE_HEADING, packageLines),
				makeSection(COMMANDS_HEADING, buildCommandLines(commands)),
			].join(SECTION_SEPARATOR);

			pi.sendMessage({
				customType: CUSTOM_MESSAGE_TYPE,
				content: report,
				display: DISPLAY_MESSAGE,
			});
		},
	});
}
