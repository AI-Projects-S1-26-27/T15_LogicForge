import React from "react";
export default class PageBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidUpdate(previous) {
    if (previous.resetKey !== this.props.resetKey && this.state.failed)
      this.setState({ failed: false });
  }
  render() {
    if (this.state.failed)
      return (
        <section className="empty-panel" role="alert">
          <h2>This view couldn’t load.</h2>
          <p>
            Return to your semester plan and regenerate to refresh saved
            diagnostics. Your course selections are still available.
          </p>
          <button
            className="primary-action"
            onClick={() => {
              this.setState({ failed: false });
              this.props.onHome();
            }}
          >
            Back to semester plan
          </button>
        </section>
      );
    return this.props.children;
  }
}
