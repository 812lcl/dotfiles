"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
class ActionableMessageItem {
    constructor(title) {
        this.title = title;
    }
    setAction(action) {
        this.action = action;
    }
    takeAction() {
        if (this.action) {
            this.action();
        }
    }
}
exports.ActionableMessageItem = ActionableMessageItem;
//# sourceMappingURL=actionablemessageitem.js.map