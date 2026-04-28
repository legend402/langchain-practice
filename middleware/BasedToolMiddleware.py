from langchain.agents.middleware import AgentMiddleware

class BasedToolMiddleware(AgentMiddleware):
  def after_model(self, state, runtime):
    return super().after_model(state, runtime)
