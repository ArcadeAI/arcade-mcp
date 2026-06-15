import ansiRegex from 'ansi-regex';

const regex = ansiRegex({onlyFirst: true});

export default function hasAnsi(string) {
	return regex.test(string);
}
