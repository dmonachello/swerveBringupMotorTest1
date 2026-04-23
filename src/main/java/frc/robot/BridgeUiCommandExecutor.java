package frc.robot;

/**
 * NAME
 *   BridgeUiCommandExecutor - Execute UI commands through ingress policy and switch delegate.
 */
final class BridgeUiCommandExecutor {

  private final BridgeUiIngressPolicy ingressPolicy;
  private final BridgeUiCommandDispatcher dispatcher;

  BridgeUiCommandExecutor(BridgeUiIngressPolicy ingressPolicy, BridgeUiCommandDispatcher dispatcher) {
    this.ingressPolicy = ingressPolicy;
    this.dispatcher = dispatcher;
  }

  BridgeUiCommandResult executeRaw(
      String name,
      String argsJson,
      double cmdTs,
      String clientId,
      boolean isTcp) {
    BridgeUiIngressPolicy.Ingress ingress = ingressPolicy.parseIngress(name, argsJson, clientId);
    BridgeUiIngressPolicy.ValidationFailure failure = ingressPolicy.validateIngress(ingress, isTcp);
    if (failure != null) {
      BridgeUiCommandResult result = new BridgeUiCommandResult();
      result.ok = false;
      result.message = failure.message;
      result.outText = failure.message;
      return result;
    }
    ingressPolicy.applyPreExecution(ingress, isTcp);
    return dispatcher.dispatch(ingress, cmdTs, isTcp);
  }
}
