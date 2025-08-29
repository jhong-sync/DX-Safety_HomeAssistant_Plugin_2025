import React, { useState, useEffect } from 'react';
import './index.css';

interface DXSafetyCardProps {
  hass: any;
  config: any;
}

interface SensorState {
  headline: string;
  level: string;
  intensity: string;
  shelter: string;
}

interface HelperValues {
  threshold_minor: number;
  threshold_moderate: number;
  threshold_severe: number;
  threshold_critical: number;
  light_severe_color: string;
  light_critical_color: string;
  sound_profile_ios: string;
  channel_android: string;
}

const DXSafetyCard: React.FC<DXSafetyCardProps> = ({ hass, config }) => {
  const [sensorState, setSensorState] = useState<SensorState>({
    headline: '로딩 중...',
    level: 'unknown',
    intensity: 'unknown',
    shelter: 'unknown'
  });

  const [helperValues, setHelperValues] = useState<HelperValues>({
    threshold_minor: 0,
    threshold_moderate: 0,
    threshold_severe: 0,
    threshold_critical: 0,
    light_severe_color: 'red',
    light_critical_color: 'red',
    sound_profile_ios: 'default',
    channel_android: 'default'
  });

  const [isLoading, setIsLoading] = useState(false);

  // 센서 상태 업데이트
  useEffect(() => {
    const updateSensorState = () => {
      const entities = hass.states;
      
      setSensorState({
        headline: entities['sensor.dxsafety_last_headline']?.state || 'Unknown',
        level: entities['sensor.dxsafety_last_level']?.state || 'unknown',
        intensity: entities['sensor.dxsafety_last_intensity']?.state || 'unknown',
        shelter: entities['sensor.dxsafety_last_shelter']?.state || 'unknown'
      });
    };

    updateSensorState();
    const interval = setInterval(updateSensorState, 5000);
    return () => clearInterval(interval);
  }, [hass.states]);

  // Helper 값 업데이트
  useEffect(() => {
    const updateHelperValues = () => {
      const entities = hass.states;
      
      setHelperValues({
        threshold_minor: parseFloat(entities['input_number.dxsafety_threshold_minor']?.state || '0'),
        threshold_moderate: parseFloat(entities['input_number.dxsafety_threshold_moderate']?.state || '0'),
        threshold_severe: parseFloat(entities['input_number.dxsafety_threshold_severe']?.state || '0'),
        threshold_critical: parseFloat(entities['input_number.dxsafety_threshold_critical']?.state || '0'),
        light_severe_color: entities['input_select.dxsafety_light_severe_color']?.state || 'red',
        light_critical_color: entities['input_select.dxsafety_light_critical_color']?.state || 'red',
        sound_profile_ios: entities['input_text.dxsafety_sound_profile_ios']?.state || 'default',
        channel_android: entities['input_text.dxsafety_channel_android']?.state || 'default'
      });
    };

    updateHelperValues();
    const interval = setInterval(updateHelperValues, 10000);
    return () => clearInterval(interval);
  }, [hass.states]);

  // Helper 값 업데이트 함수
  const updateHelperValue = async (entityId: string, value: string | number) => {
    try {
      await hass.callService('input_text', 'set_value', {
        entity_id: entityId,
        value: value.toString()
      });
    } catch (error) {
      console.error('Failed to update helper value:', error);
    }
  };

  // 테스트 알림 발행
  const sendTestAlert = async () => {
    setIsLoading(true);
    try {
      await hass.callService('homeassistant', 'fire_event', {
        event_type: 'dxsafety_alert',
        event_data: {
          headline: '테스트 경보',
          description: '이것은 테스트 알림입니다',
          intensity_value: 'moderate',
          level: 'moderate',
          shelter: { name: '테스트 대피소' },
          links: ['https://example.com/test']
        }
      });
      // 성공 메시지 표시
      setTimeout(() => setIsLoading(false), 2000);
    } catch (error) {
      console.error('Failed to send test alert:', error);
      setIsLoading(false);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'minor': return 'text-blue-600';
      case 'moderate': return 'text-yellow-600';
      case 'severe': return 'text-orange-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="dxsafety-card bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">DX-Safety 모니터링</h2>
        <p className="text-gray-600">재난 경보 상태 및 설정 관리</p>
      </div>

      {/* 센서 상태 섹션 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">현재 상태</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">헤드라인:</span>
              <span className="font-medium">{sensorState.headline}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">레벨:</span>
              <span className={`font-medium ${getLevelColor(sensorState.level)}`}>
                {sensorState.level}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">강도:</span>
              <span className="font-medium">{sensorState.intensity}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">대피소:</span>
              <span className="font-medium">{sensorState.shelter}</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">테스트</h3>
          <button
            onClick={sendTestAlert}
            disabled={isLoading}
            className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
              isLoading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isLoading ? '발행 중...' : '테스트 알림 보내기'}
          </button>
          <p className="text-sm text-gray-500 mt-2">
            샘플 dxsafety_alert 이벤트를 발행합니다
          </p>
        </div>
      </div>

      {/* Helper 설정 섹션 */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">정책 설정</h3>
        
        {/* 임계값 설정 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <h4 className="text-md font-medium text-gray-600 mb-3">임계값 설정</h4>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Minor:</label>
                <input
                  type="number"
                  value={helperValues.threshold_minor}
                  onChange={(e) => updateHelperValue('input_number.dxsafety_threshold_minor', e.target.value)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Moderate:</label>
                <input
                  type="number"
                  value={helperValues.threshold_moderate}
                  onChange={(e) => updateHelperValue('input_number.dxsafety_threshold_moderate', e.target.value)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Severe:</label>
                <input
                  type="number"
                  value={helperValues.threshold_severe}
                  onChange={(e) => updateHelperValue('input_number.dxsafety_threshold_severe', e.target.value)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Critical:</label>
                <input
                  type="number"
                  value={helperValues.threshold_critical}
                  onChange={(e) => updateHelperValue('input_number.dxsafety_threshold_critical', e.target.value)}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-md font-medium text-gray-600 mb-3">알림 설정</h4>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Severe 색상:</label>
                <select
                  value={helperValues.light_severe_color}
                  onChange={(e) => updateHelperValue('input_select.dxsafety_light_severe_color', e.target.value)}
                  className="px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="red">빨강</option>
                  <option value="orange">주황</option>
                  <option value="yellow">노랑</option>
                </select>
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Critical 색상:</label>
                <select
                  value={helperValues.light_critical_color}
                  onChange={(e) => updateHelperValue('input_select.dxsafety_light_critical_color', e.target.value)}
                  className="px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="red">빨강</option>
                  <option value="orange">주황</option>
                  <option value="yellow">노랑</option>
                </select>
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">iOS 사운드:</label>
                <input
                  type="text"
                  value={helperValues.sound_profile_ios}
                  onChange={(e) => updateHelperValue('input_text.dxsafety_sound_profile_ios', e.target.value)}
                  className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
              <div className="flex justify-between items-center">
                <label className="text-sm text-gray-600">Android 채널:</label>
                <input
                  type="text"
                  value={helperValues.channel_android}
                  onChange={(e) => updateHelperValue('input_text.dxsafety_channel_android', e.target.value)}
                  className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DXSafetyCard;
