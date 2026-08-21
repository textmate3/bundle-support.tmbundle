require 'test/unit'
require 'tempfile'

# Let scriptmate resolve its Bundle Support requires against this checkout.
ENV['TM_SUPPORT_PATH'] = File.expand_path('..', __dir__)
require "#{ENV['TM_SUPPORT_PATH']}/lib/scriptmate"

# Regression test: scriptmate hands the write end of an error pipe to the
# child process through ENV['TM_ERROR_FD'], and RubyMate's catch_exception
# writes its formatted exception report there via IO.for_fd. IO.pipe
# descriptors are close-on-exec by default since Ruby 2.0, so without an
# explicit opt-out the descriptor died at exec and every exception report
# failed with Errno::EBADF instead of rendering.
class ScriptMateErrorFdTest < Test::Unit::TestCase
  class ErrorFdProbeScript < UserScript
    def executable
      'ruby'
    end

    def args
      ['-e', e_sh("io = IO.for_fd(ENV['TM_ERROR_FD'].to_i); io.write 'error-fd-ok'; io.close")]
    end
  end

  def setup
    @original_env = ENV.to_hash
    probe = Tempfile.create(['error_fd_probe', '.rb'])
    probe.close
    @probe_path = probe.path
    ENV['TM_FILEPATH'] = @probe_path
    ENV.delete('TM_PID')
  end

  def teardown
    File.unlink(@probe_path) rescue nil
    ENV.replace(@original_env)
  end

  def test_child_process_can_write_to_the_error_fd
    script = ErrorFdProbeScript.new('')
    from_child = nil
    script.run do |stdout, stderr, error_io, pid|
      Process.wait(pid)
      from_child = error_io.read
    end
    assert_equal('error-fd-ok', from_child)
  end
end
