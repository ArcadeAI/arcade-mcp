export type changeType =
	| "added"
	| "copied"
	| "deleted"
	| "modified"
	| "renamed"
	| "type changed"
	| "unmerged"
	| "pairing broken"
	| "unknown"
	| "unmodified"
	| "untracked"
	| "ignored";

export interface IChange {
	/**
	 * name of the file
	 */
	name: string;
	/**
	 * similarity percentage for renamed files (0-100)
	 */
	similarity?: number;
	/**
	 * how the file was changed
	 */
	type: changeType;
	/**
	 * if the file was renamed: what the old file's name was
	 */
	oldName?: string;
}

export type outputTypeType = "regex" | "json";

export interface IBaseOptions {
	/**
	 * The revision against which to compare. When not passed defaults to the
	 * _current_ commit hash (if there's any)
	 */
	oldRevision?: string;
	/**
	 * Newer revision against which to compare. Leave out when you want to
	 * compare against the working tree
	 */
	newRevision?: string;
	/**
	 * When true only takes already tracked files into account.
	 * When false also takes untracked files into account (default)
	 */
	trackedOnly?: boolean;
}

export interface IFormatOptions extends IBaseOptions {
	/**
	 * The type of output to deliver.
	 */
	outputType: "regex" | "json";

	/**
	 * A comma-separated list of file extensions to include in the output.
	 * When the list includes "*" all files are included. Currently applicable
	 * to the "regex" outputType only.
	 */
	extensions: string;
}

export interface IInternalOptions extends IBaseOptions {
	/**
	 * The type of output to deliver. undefined/ left out
	 * the outputType defaults to a list of `IChange`s
	 */
	outputType?: undefined;
}

export type IOptions = IFormatOptions | IInternalOptions;

/**
 * promises a list of files changed since pOldRevision.
 *
 * @throws {Error}
 */
export function list(pOptions?: IInternalOptions): Promise<IChange[]>;

/**
 * promises a list of files changed since pOldRevision, formatted
 * into a string as a pOptions.outputType
 *
 * @throws {Error}
 */
export function list(pOptions?: IFormatOptions): Promise<string>;

/**
 * Promises the SHA1 of the current HEAD
 *
 * @throws {Error}
 */
export function getSHA(): Promise<string>;
