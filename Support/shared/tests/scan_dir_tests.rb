require 'test/unit'

# Let textmate.rb resolve its Bundle Support requires against this checkout.
ENV['TM_SUPPORT_PATH'] = File.expand_path('..', __dir__)
require "#{ENV['TM_SUPPORT_PATH']}/lib/textmate"

# Regression test: TextMate.each_text_file walks a project via
# ProjectFileFilter#binary?, which classifies unknown files by matching
# file(1) output against regexps. That output is not guaranteed to be valid
# UTF-8, and matching a regexp against an invalid UTF-8 string raises
# ArgumentError since Ruby 1.9, which killed whole-project scans (the Show
# TODO List command) on the first odd file. binary? now matches raw bytes.
#
# The fixtures/bin/file shim reproduces the poisonous output deterministically
# for one fixture and delegates to the real file(1) for everything else.
class ScanDirTest < Test::Unit::TestCase
  FIXTURES = File.expand_path('fixtures/scan', __dir__)
  FAKE_BIN = File.expand_path('fixtures/bin', __dir__)

  def setup
    @original_env = ENV.to_hash
    ENV['PATH'] = "#{FAKE_BIN}:#{ENV['PATH']}"
    # Point preferences lookups at nothing so ProjectFileFilter uses its
    # built-in defaults instead of this machine's real TextMate preferences.
    ENV['TM_APP_IDENTIFIER'] = 'org.textmate3.tests.no-preferences'
    ENV['TM_PROJECT_DIRECTORY'] = FIXTURES
    ENV.delete('TM_SELECTED_FILES')
    ENV.delete('TM_SELECTED_FILE')
    ENV.delete('TM_FILEPATH')
  end

  def teardown
    ENV.replace(@original_env)
  end

  def test_scan_survives_file_output_that_is_not_valid_utf8
    seen = []
    assert_nothing_raised do
      TextMate.each_text_file { |path| seen << File.basename(path) }
    end
    assert_include(seen, 'plain.txt')
    assert_not_include(seen, 'nasty_interpreter',
      'the poisonous fixture should be classified binary and skipped, not yielded')
  end
end
