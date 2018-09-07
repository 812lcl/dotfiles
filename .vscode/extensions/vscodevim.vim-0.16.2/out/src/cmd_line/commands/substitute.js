"use strict";
/* tslint:disable:no-bitwise */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : new P(function (resolve) { resolve(result.value); }).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const node = require("../node");
const token = require("../token");
const error_1 = require("../../error");
const textEditor_1 = require("../../textEditor");
const configuration_1 = require("../../configuration/configuration");
const decoration_1 = require("../../configuration/decoration");
/**
 * The flags that you can use for the substitute commands:
 * [&] Must be the first one: Keep the flags from the previous substitute command.
 * [c] Confirm each substitution.
 * [e] When the search pattern fails, do not issue an error message and, in
 *     particular, continue in maps as if no error occurred.
 * [g] Replace all occurrences in the line.  Without this argument, replacement
 *     occurs only for the first occurrence in each line.
 * [i] Ignore case for the pattern.
 * [I] Don't ignore case for the pattern.
 * [n] Report the number of matches, do not actually substitute.
 * [p] Print the line containing the last substitute.
 * [#] Like [p] and prepend the line number.
 * [l] Like [p] but print the text like |:list|.
 * [r] When the search pattern is empty, use the previously used search pattern
 *     instead of the search pattern from the last substitute or ":global".
 */
var SubstituteFlags;
(function (SubstituteFlags) {
    SubstituteFlags[SubstituteFlags["None"] = 0] = "None";
    SubstituteFlags[SubstituteFlags["KeepPreviousFlags"] = 1] = "KeepPreviousFlags";
    SubstituteFlags[SubstituteFlags["ConfirmEach"] = 2] = "ConfirmEach";
    SubstituteFlags[SubstituteFlags["SuppressError"] = 4] = "SuppressError";
    SubstituteFlags[SubstituteFlags["ReplaceAll"] = 8] = "ReplaceAll";
    SubstituteFlags[SubstituteFlags["IgnoreCase"] = 16] = "IgnoreCase";
    SubstituteFlags[SubstituteFlags["NoIgnoreCase"] = 32] = "NoIgnoreCase";
    SubstituteFlags[SubstituteFlags["PrintCount"] = 64] = "PrintCount";
    SubstituteFlags[SubstituteFlags["PrintLastMatchedLine"] = 128] = "PrintLastMatchedLine";
    SubstituteFlags[SubstituteFlags["PrintLastMatchedLineWithNumber"] = 256] = "PrintLastMatchedLineWithNumber";
    SubstituteFlags[SubstituteFlags["PrintLastMatchedLineWithList"] = 512] = "PrintLastMatchedLineWithList";
    SubstituteFlags[SubstituteFlags["UsePreviousPattern"] = 1024] = "UsePreviousPattern";
})(SubstituteFlags = exports.SubstituteFlags || (exports.SubstituteFlags = {}));
class SubstituteCommand extends node.CommandBase {
    constructor(args) {
        super();
        this.neovimCapable = true;
        this._name = 'search';
        this._arguments = args;
        this._abort = false;
    }
    get arguments() {
        return this._arguments;
    }
    getRegex(args, vimState) {
        let jsRegexFlags = '';
        if (configuration_1.configuration.substituteGlobalFlag === true) {
            // the gdefault flag is on, then /g if on by default and /g negates that
            if (!(args.flags & SubstituteFlags.ReplaceAll)) {
                jsRegexFlags += 'g';
            }
        }
        else {
            // the gdefault flag is off, then /g means replace all
            if (args.flags & SubstituteFlags.ReplaceAll) {
                jsRegexFlags += 'g';
            }
        }
        if (args.flags & SubstituteFlags.IgnoreCase) {
            jsRegexFlags += 'i';
        }
        // If no pattern is entered, use previous search state (including search with * and #)
        if (args.pattern === '') {
            const prevSearchState = vimState.globalState.searchState;
            if (prevSearchState === undefined || prevSearchState.searchString === '') {
                throw error_1.VimError.fromCode(error_1.ErrorCode.E35);
            }
            else {
                args.pattern = prevSearchState.searchString;
            }
        }
        return new RegExp(args.pattern, jsRegexFlags);
    }
    replaceTextAtLine(line, regex, vimState) {
        return __awaiter(this, void 0, void 0, function* () {
            const originalContent = textEditor_1.TextEditor.readLineAt(line);
            if (!regex.test(originalContent)) {
                return;
            }
            if (this._arguments.flags & SubstituteFlags.ConfirmEach) {
                // Loop through each match on this line and get confirmation before replacing
                let newContent = originalContent;
                const matches = newContent.match(regex);
                var nonGlobalRegex = new RegExp(regex.source, regex.flags.replace('g', ''));
                let matchPos = 0;
                for (const match of matches) {
                    if (this._abort) {
                        break;
                    }
                    matchPos = newContent.indexOf(match, matchPos);
                    if (!(this._arguments.flags & SubstituteFlags.ConfirmEach) ||
                        (yield this.confirmReplacement(regex.source, line, vimState, match, matchPos))) {
                        newContent = newContent.replace(nonGlobalRegex, this._arguments.replace);
                        yield textEditor_1.TextEditor.replace(new vscode.Range(line, 0, line, originalContent.length), newContent);
                    }
                    matchPos += match.length;
                }
            }
            else {
                yield textEditor_1.TextEditor.replace(new vscode.Range(line, 0, line, originalContent.length), originalContent.replace(regex, this._arguments.replace));
            }
        });
    }
    confirmReplacement(replacement, line, vimState, match, matchIndex) {
        return __awaiter(this, void 0, void 0, function* () {
            const cancellationToken = new vscode.CancellationTokenSource();
            const validSelections = ['y', 'n', 'a', 'q', 'l'];
            let selection = '';
            const searchRanges = [
                new vscode.Range(line, matchIndex, line, matchIndex + match.length),
            ];
            vimState.editor.revealRange(new vscode.Range(line, 0, line, 0));
            vimState.editor.setDecorations(decoration_1.Decoration.SearchHighlight, searchRanges);
            const prompt = `Replace with ${replacement} (${validSelections.join('/')})?`;
            yield vscode.window.showInputBox({
                ignoreFocusOut: true,
                prompt,
                placeHolder: validSelections.join('/'),
                validateInput: (input) => {
                    if (validSelections.indexOf(input) >= 0) {
                        selection = input;
                        cancellationToken.cancel();
                    }
                    return prompt;
                },
            }, cancellationToken.token);
            if (selection === 'q' || selection === 'l' || !selection) {
                this._abort = true;
            }
            else if (selection === 'a') {
                this._arguments.flags = this._arguments.flags & ~SubstituteFlags.ConfirmEach;
            }
            return selection === 'y' || selection === 'a' || selection === 'l';
        });
    }
    execute(vimState) {
        return __awaiter(this, void 0, void 0, function* () {
            const regex = this.getRegex(this._arguments, vimState);
            const selection = vimState.editor.selection;
            const line = selection.start.isBefore(selection.end)
                ? selection.start.line
                : selection.end.line;
            if (!this._abort) {
                yield this.replaceTextAtLine(line, regex, vimState);
            }
        });
    }
    executeWithRange(vimState, range) {
        return __awaiter(this, void 0, void 0, function* () {
            let startLine;
            let endLine;
            if (range.left[0].type === token.TokenType.Percent) {
                startLine = new vscode.Position(0, 0);
                endLine = new vscode.Position(textEditor_1.TextEditor.getLineCount() - 1, 0);
            }
            else {
                startLine = range.lineRefToPosition(vimState.editor, range.left, vimState);
                endLine = range.lineRefToPosition(vimState.editor, range.right, vimState);
            }
            if (this._arguments.count && this._arguments.count >= 0) {
                startLine = endLine;
                endLine = new vscode.Position(endLine.line + this._arguments.count - 1, 0);
            }
            // TODO: Global Setting.
            // TODO: There are differencies between Vim Regex and JS Regex.
            let regex = this.getRegex(this._arguments, vimState);
            for (let currentLine = startLine.line; currentLine <= endLine.line && currentLine < textEditor_1.TextEditor.getLineCount(); currentLine++) {
                if (this._abort) {
                    break;
                }
                yield this.replaceTextAtLine(currentLine, regex, vimState);
            }
        });
    }
}
exports.SubstituteCommand = SubstituteCommand;

//# sourceMappingURL=substitute.js.map
