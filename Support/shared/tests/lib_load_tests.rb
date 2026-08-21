require 'test/unit'
require 'open3'

ENV['TM_SUPPORT_PATH'] = File.expand_path('..', __dir__)

# Load sanity for the shared libraries: each core lib must at least require
# cleanly, both under the target Ruby running this suite and under the system
# /usr/bin/ruby that the GUI application's bare PATH still resolves for
# command shebangs. A syntax error or load-time evaluation mistake in these
# files breaks every bundle command that requires them, so catching it here
# is much cheaper than finding it in an in-app error window.
class LibLoadTest < Test::Unit::TestCase
  CORE_LIBS = %w[
    escape
    exit_codes
    io
    progress
    scriptmate
    textmate
    ui
    web_preview
    tm/executor
    tm/htmloutput
    tm/process
    tm/tempfile
  ].freeze

  def interpreters
    [RbConfig.ruby, '/usr/bin/ruby'].select { |ruby| File.executable?(ruby) }
  end

  def test_core_libs_load_under_every_interpreter
    failures = []
    interpreters.each do |ruby|
      CORE_LIBS.each do |lib|
        code = "require ENV['TM_SUPPORT_PATH'] + '/lib/#{lib}'"
        # Scrub the terminal's Ruby version manager environment so the system
        # interpreter is not poisoned by another Ruby's installed gems. The
        # GUI application launches commands without these variables.
        subprocess_env = {
          'TM_SUPPORT_PATH' => ENV['TM_SUPPORT_PATH'],
          'GEM_HOME'        => nil,
          'GEM_PATH'        => nil,
          'GEM_ROOT'        => nil,
          'RUBYLIB'         => nil,
          'RUBYOPT'         => nil,
        }
        output, status = Open3.capture2e(subprocess_env, ruby, '-e', code)
        failures << "#{ruby} — #{lib}:\n#{output}" unless status.success?
      end
    end
    assert(failures.empty?, "libraries failed to load:\n\n#{failures.join("\n")}")
  end
end
