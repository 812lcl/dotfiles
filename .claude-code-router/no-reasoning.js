// no-reasoning.js
module.exports = class NoReasoningTransformer {
  static TransformerName = 'no-reasoning';

  constructor(options) {
    this.name = 'no-reasoning';
    this.options = options || {};
  }

  async transformRequestIn(request, provider, context) {
    // 删除 reasoning 字段
    if (request.reasoning) {
      delete request.reasoning;
    }
    return request;
  }

  async auth(request, provider, context) {
    const headers = {
      'authorization': `Bearer ${provider.apiKey}`
    };
    return {
      body: request,
      config: { headers }
    };
  }
};
